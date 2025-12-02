"""图片生成服务"""
import logging
import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List, Optional, Tuple
from backend.config import Config
from backend.generators.factory import ImageGeneratorFactory
from backend.utils.image_compressor import compress_image

logger = logging.getLogger(__name__)


class ImageService:
    """图片生成服务类"""

    # 并发配置
    MAX_CONCURRENT = 15  # 最大并发数
    AUTO_RETRY_COUNT = 3  # 自动重试次数

    def __init__(self, provider_name: str = None):
        """
        初始化图片生成服务

        Args:
            provider_name: 服务商名称，如果为None则使用配置文件中的激活服务商
        """
        logger.debug("初始化 ImageService...")

        # 获取服务商配置
        if provider_name is None:
            provider_name = Config.get_active_image_provider()

        logger.info(f"使用图片服务商: {provider_name}")
        provider_config = Config.get_image_provider_config(provider_name)

        # 创建生成器实例
        provider_type = provider_config.get('type', provider_name)
        logger.debug(f"创建生成器: type={provider_type}")
        self.generator = ImageGeneratorFactory.create(provider_type, provider_config)

        # 保存配置信息
        self.provider_name = provider_name
        self.provider_config = provider_config

        # 检查是否启用短 prompt 模式
        self.use_short_prompt = provider_config.get('short_prompt', False)

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        self.prompt_template_short = self._load_prompt_template(short=True)

        # 历史记录根目录
        self.history_root_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_root_dir, exist_ok=True)

        # 当前任务的输出目录（每个任务一个子文件夹）
        self.current_task_dir = None

        # 存储任务状态（用于重试）
        self._task_states: Dict[str, Dict] = {}

        logger.info(f"ImageService 初始化完成: provider={provider_name}, type={provider_type}")

    def _load_prompt_template(self, short: bool = False) -> str:
        """加载 Prompt 模板"""
        filename = "image_prompt_short.txt" if short else "image_prompt.txt"
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            filename
        )
        if not os.path.exists(prompt_path):
            # 如果短模板不存在，返回空字符串
            return ""
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _save_image(self, image_data: bytes, filename: str, task_dir: str = None) -> str:
        """
        保存图片到本地，同时生成缩略图

        Args:
            image_data: 图片二进制数据
            filename: 文件名
            task_dir: 任务目录（如果为None则使用当前任务目录）

        Returns:
            保存的文件路径
        """
        if task_dir is None:
            task_dir = self.current_task_dir

        if task_dir is None:
            raise ValueError("任务目录未设置")

        # 保存原图
        filepath = os.path.join(task_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        # 生成缩略图（50KB左右）
        thumbnail_data = compress_image(image_data, max_size_kb=50)
        thumbnail_filename = f"thumb_{filename}"
        thumbnail_path = os.path.join(task_dir, thumbnail_filename)
        with open(thumbnail_path, "wb") as f:
            f.write(thumbnail_data)

        return filepath

    def _generate_single_image(
        self,
        page: Dict,
        task_id: str,
        reference_image: Optional[bytes] = None,
        retry_count: int = 0,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = ""
    ) -> Tuple[int, bool, Optional[str], Optional[str]]:
        """
        生成单张图片（带自动重试）

        Args:
            page: 页面数据
            task_id: 任务ID
            reference_image: 参考图片（封面图）
            retry_count: 当前重试次数
            full_outline: 完整的大纲文本
            user_images: 用户上传的参考图片列表
            user_topic: 用户原始输入

        Returns:
            (index, success, filename, error_message)
        """
        index = page["index"]
        page_type = page["type"]
        page_content = page["content"]

        max_retries = self.AUTO_RETRY_COUNT

        for attempt in range(max_retries):
            try:
                logger.debug(f"生成图片 [{index}]: type={page_type}, attempt={attempt + 1}/{max_retries}")

                # 根据配置选择模板（短 prompt 或完整 prompt）
                if self.use_short_prompt and self.prompt_template_short:
                    # 短 prompt 模式：只包含页面类型和内容
                    prompt = self.prompt_template_short.format(
                        page_content=page_content,
                        page_type=page_type
                    )
                    logger.debug(f"  使用短 prompt 模式 ({len(prompt)} 字符)")
                else:
                    # 完整 prompt 模式：包含大纲和用户需求
                    prompt = self.prompt_template.format(
                        page_content=page_content,
                        page_type=page_type,
                        full_outline=full_outline,
                        user_topic=user_topic if user_topic else "未提供"
                    )

                # 打印详细的生成参数日志
                logger.info(f"🎨 开始生成图片 [{index}] (Attempt {attempt + 1}/{max_retries})")
                logger.info(f"📋 Prompt 内容:\n{prompt}")
                logger.info(f"⚙️ 生成参数: Provider={self.provider_config.get('type')}, Model={self.provider_config.get('model')}")

                # 调用生成器生成图片
                if self.provider_config.get('type') == 'google_genai':
                    logger.debug(f"  使用 Google GenAI 生成器")
                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                        temperature=self.provider_config.get('temperature', 1.0),
                        model=self.provider_config.get('model', 'gemini-3-pro-image-preview'),
                        reference_image=reference_image,
                    )
                elif self.provider_config.get('type') == 'image_api':
                    logger.debug(f"  使用 Image API 生成器")
                    # Image API 支持多张参考图片
                    # 组合参考图片：用户上传的图片 + 封面图
                    reference_images = []
                    if user_images:
                        reference_images.extend(user_images)
                    if reference_image:
                        reference_images.append(reference_image)

                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                        temperature=self.provider_config.get('temperature', 1.0),
                        model=self.provider_config.get('model', 'nano-banana-2'),
                        reference_images=reference_images if reference_images else None,
                    )
                elif self.provider_config.get('type') == 'modelscope':
                    logger.debug(f"  使用 ModelScope 生成器")
                    image_data = self.generator.generate_image(
                        prompt=prompt
                    )
                else:
                    logger.debug(f"  使用 OpenAI 兼容生成器")
                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        size=self.provider_config.get('default_size', '1024x1024'),
                        model=self.provider_config.get('model'),
                        quality=self.provider_config.get('quality', 'standard'),
                    )

                # 保存图片（使用当前任务目录）
                filename = f"{index}.png"
                self._save_image(image_data, filename, self.current_task_dir)
                logger.info(f"✅ 图片 [{index}] 生成成功: {filename}")

                return (index, True, filename, None)

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"图片 [{index}] 生成失败 (尝试 {attempt + 1}/{max_retries}): {error_msg[:200]}")

                if attempt < max_retries - 1:
                    # 等待后重试
                    wait_time = 2 ** attempt
                    logger.debug(f"  等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue

                logger.error(f"❌ 图片 [{index}] 生成失败，已达最大重试次数")
                return (index, False, None, error_msg)

        return (index, False, None, "超过最大重试次数")

    def generate_images(
        self,
        pages: list,
        task_id: str = None,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = ""
    ) -> Generator[Dict[str, Any], None, None]:
        """
        生成图片（生成器，支持 SSE 流式返回）
        优化版本：先生成封面，然后并发生成其他页面

        Args:
            pages: 页面列表
            task_id: 任务 ID（可选）
            full_outline: 完整的大纲文本（用于保持风格一致）
            user_images: 用户上传的参考图片列表（可选）
            user_topic: 用户原始输入（用于保持意图一致）

        Yields:
            进度事件字典
        """
        if task_id is None:
            task_id = f"task_{uuid.uuid4().hex[:8]}"

        logger.info(f"开始图片生成任务: task_id={task_id}, pages={len(pages)}")

        # 创建任务专属目录
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)
        logger.debug(f"任务目录: {self.current_task_dir}")

        total = len(pages)
        generated_images = []
        failed_pages = []
        cover_image_data = None

        # 压缩用户上传的参考图到200KB以内（减少内存和传输开销）
        compressed_user_images = None
        if user_images:
            compressed_user_images = [compress_image(img, max_size_kb=200) for img in user_images]

        # 初始化任务状态
        self._task_states[task_id] = {
            "pages": pages,
            "generated": {},
            "failed": {},
            "cover_image": None,
            "full_outline": full_outline,
            "user_images": compressed_user_images,
            "user_topic": user_topic
        }

        # ==================== 第一阶段：生成封面 ====================
        cover_page = None
        other_pages = []

        for page in pages:
            if page["type"] == "cover":
                cover_page = page
            else:
                other_pages.append(page)

        # 如果没有封面，使用第一页作为封面
        if cover_page is None and len(pages) > 0:
            cover_page = pages[0]
            other_pages = pages[1:]

        if cover_page:
            # 发送封面生成进度
            yield {
                "event": "progress",
                "data": {
                    "index": cover_page["index"],
                    "status": "generating",
                    "message": "正在生成封面...",
                    "current": 1,
                    "total": total,
                    "phase": "cover"
                }
            }

            # 生成封面（使用用户上传的图片作为参考）
            index, success, filename, error = self._generate_single_image(
                cover_page, task_id, reference_image=None, full_outline=full_outline,
                user_images=compressed_user_images, user_topic=user_topic
            )

            if success:
                generated_images.append(filename)
                self._task_states[task_id]["generated"][index] = filename

                # 读取封面图片作为参考，并立即压缩到200KB以内
                cover_path = os.path.join(self.current_task_dir, filename)
                with open(cover_path, "rb") as f:
                    cover_image_data = f.read()

                # 压缩封面图（减少内存占用和后续传输开销）
                cover_image_data = compress_image(cover_image_data, max_size_kb=200)
                self._task_states[task_id]["cover_image"] = cover_image_data

                yield {
                    "event": "complete",
                    "data": {
                        "index": index,
                        "status": "done",
                        "image_url": f"/api/images/{task_id}/{filename}",
                        "phase": "cover"
                    }
                }
            else:
                failed_pages.append(cover_page)
                self._task_states[task_id]["failed"][index] = error

                yield {
                    "event": "error",
                    "data": {
                        "index": index,
                        "status": "error",
                        "message": error,
                        "retryable": True,
                        "phase": "cover"
                    }
                }

        # ==================== 第二阶段：生成其他页面 ====================
        if other_pages:
            # 检查是否启用高并发模式
            high_concurrency = self.provider_config.get('high_concurrency', False)

            if high_concurrency:
                # 高并发模式：并行生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始并发生成 {len(other_pages)} 页内容...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content"
                    }
                }

                # 使用线程池并发生成
                with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                    # 提交所有任务
                    future_to_page = {
                        executor.submit(
                            self._generate_single_image,
                            page,
                            task_id,
                            cover_image_data,  # 使用封面作为参考
                            0,  # retry_count
                            full_outline,  # 传入完整大纲
                            compressed_user_images,  # 用户上传的参考图片（已压缩）
                            user_topic  # 用户原始输入
                        ): page
                        for page in other_pages
                    }

                    # 发送每个页面的进度
                    for page in other_pages:
                        yield {
                            "event": "progress",
                            "data": {
                                "index": page["index"],
                                "status": "generating",
                                "current": len(generated_images) + 1,
                                "total": total,
                                "phase": "content"
                            }
                        }

                    # 收集结果
                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            index, success, filename, error = future.result()

                            if success:
                                generated_images.append(filename)
                                self._task_states[task_id]["generated"][index] = filename

                                yield {
                                    "event": "complete",
                                    "data": {
                                        "index": index,
                                        "status": "done",
                                        "image_url": f"/api/images/{task_id}/{filename}",
                                        "phase": "content"
                                    }
                                }
                            else:
                                failed_pages.append(page)
                                self._task_states[task_id]["failed"][index] = error

                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": index,
                                        "status": "error",
                                        "message": error,
                                        "retryable": True,
                                        "phase": "content"
                                    }
                                }

                        except Exception as e:
                            failed_pages.append(page)
                            error_msg = str(e)
                            self._task_states[task_id]["failed"][page["index"]] = error_msg

                            yield {
                                "event": "error",
                                "data": {
                                    "index": page["index"],
                                    "status": "error",
                                    "message": error_msg,
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }
            else:
                # 顺序模式：逐个生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始顺序生成 {len(other_pages)} 页内容...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content"
                    }
                }

                for page in other_pages:
                    # 发送生成进度
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": "content"
                        }
                    }

                    # 生成单张图片
                    index, success, filename, error = self._generate_single_image(
                        page,
                        task_id,
                        cover_image_data,
                        0,
                        full_outline,
                        compressed_user_images,
                        user_topic
                    )

                    if success:
                        generated_images.append(filename)
                        self._task_states[task_id]["generated"][index] = filename

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}",
                                "phase": "content"
                            }
                        }
                    else:
                        failed_pages.append(page)
                        self._task_states[task_id]["failed"][index] = error

                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True,
                                "phase": "content"
                            }
                        }

        # ==================== 完成 ====================
        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "task_id": task_id,
                "images": generated_images,
                "total": total,
                "completed": len(generated_images),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }

    def retry_single_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = ""
    ) -> Dict[str, Any]:
        """
        重试生成单张图片

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考
            full_outline: 完整大纲文本（从前端传入）
            user_topic: 用户原始输入（从前端传入）

        Returns:
            生成结果
        """
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        reference_image = None
        user_images = None

        # 首先尝试从任务状态中获取上下文
        if task_id in self._task_states:
            task_state = self._task_states[task_id]
            if use_reference:
                reference_image = task_state.get("cover_image")
            # 如果没有传入上下文，则使用任务状态中的
            if not full_outline:
                full_outline = task_state.get("full_outline", "")
            if not user_topic:
                user_topic = task_state.get("user_topic", "")
            user_images = task_state.get("user_images")

        # 如果任务状态中没有封面图，尝试从文件系统加载
        if use_reference and reference_image is None:
            cover_path = os.path.join(self.current_task_dir, "0.png")
            if os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                # 压缩封面图到 200KB
                reference_image = compress_image(cover_data, max_size_kb=200)

        index, success, filename, error = self._generate_single_image(
            page,
            task_id,
            reference_image,
            0,
            full_outline,
            user_images,
            user_topic
        )

        if success:
            if task_id in self._task_states:
                self._task_states[task_id]["generated"][index] = filename
                if index in self._task_states[task_id]["failed"]:
                    del self._task_states[task_id]["failed"][index]

            return {
                "success": True,
                "index": index,
                "image_url": f"/api/images/{task_id}/{filename}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": error,
                "retryable": True
            }

    def retry_failed_images(
        self,
        task_id: str,
        pages: List[Dict]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        批量重试失败的图片

        Args:
            task_id: 任务ID
            pages: 需要重试的页面列表

        Yields:
            进度事件
        """
        # 获取参考图
        reference_image = None
        if task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")

        total = len(pages)
        success_count = 0
        failed_count = 0

        yield {
            "event": "retry_start",
            "data": {
                "total": total,
                "message": f"开始重试 {total} 张失败的图片"
            }
        }

        # 并发重试
        # 从任务状态中获取完整大纲
        full_outline = ""
        if task_id in self._task_states:
            full_outline = self._task_states[task_id].get("full_outline", "")

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
            future_to_page = {
                executor.submit(
                    self._generate_single_image,
                    page,
                    task_id,
                    reference_image,
                    0,  # retry_count
                    full_outline  # 传入完整大纲
                ): page
                for page in pages
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    index, success, filename, error = future.result()

                    if success:
                        success_count += 1
                        if task_id in self._task_states:
                            self._task_states[task_id]["generated"][index] = filename
                            if index in self._task_states[task_id]["failed"]:
                                del self._task_states[task_id]["failed"][index]

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}"
                            }
                        }
                    else:
                        failed_count += 1
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True
                            }
                        }

                except Exception as e:
                    failed_count += 1
                    yield {
                        "event": "error",
                        "data": {
                            "index": page["index"],
                            "status": "error",
                            "message": str(e),
                            "retryable": True
                        }
                    }

        yield {
            "event": "retry_finish",
            "data": {
                "success": failed_count == 0,
                "total": total,
                "completed": success_count,
                "failed": failed_count
            }
        }

    def regenerate_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = ""
    ) -> Dict[str, Any]:
        """
        重新生成图片（用户手动触发，即使成功的也可以重新生成）

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考
            full_outline: 完整大纲文本
            user_topic: 用户原始输入

        Returns:
            生成结果
        """
        return self.retry_single_image(
            task_id, page, use_reference,
            full_outline=full_outline,
            user_topic=user_topic
        )

    def get_image_path(self, task_id: str, filename: str) -> str:
        """
        获取图片完整路径

        Args:
            task_id: 任务ID
            filename: 文件名

        Returns:
            完整路径
        """
        task_dir = os.path.join(self.history_root_dir, task_id)
        return os.path.join(task_dir, filename)

    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self._task_states.get(task_id)

    def cleanup_task(self, task_id: str):
        """清理任务状态（释放内存）"""
        if task_id in self._task_states:
            del self._task_states[task_id]


# 全局服务实例
_service_instance = None

def get_image_service() -> ImageService:
    """获取全局图片生成服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageService()
    return _service_instance

def reset_image_service():
    """重置全局服务实例（配置更新后调用）"""
    global _service_instance
    _service_instance = None
