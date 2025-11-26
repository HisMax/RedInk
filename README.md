![](images/logo.png)

---

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org/)

# 红墨 - 小红书AI图文生成器

> 让传播不再需要门槛，让创作从未如此简单

![](images/index.gif)

<p align="center">
  <em>红墨首页</em>
</p>

<p align="center">
  <img src="images/showcase-grid.png" alt="使用红墨生成的各类小红书封面" width="600"/>
</p>

<p align="center">
  <em>使用红墨生成的各类小红书封面 - AI驱动，风格统一，文字准确</em>
</p>



## 写在前面

前段时间默子在 Linux.do 发了一个用 Nano banana Pro 做 PPT 的帖子,收获了 600 多个赞。很多人用🍌Nano banana Pro 去做产品宣传图、直接生成漫画等等。我就在想:**为什么不拿🍌2来做点更功利、更刺激的事情?**

于是就有了这个项目。一句话一张图片生成小红书图文

---

## ✨ 效果展示

### 输入一句话,就能生成完整的小红书图文

#### 提示词：秋季显白美甲（暗广一个：默子牌美甲），图片 是我的小红书主页。符合我的风格生成

#### 同时我还截图了我的小红书主页，包括我的头像，签名，背景，姓名什么的

![示例1](./images/example-1.png)

#### 然后等待10-20秒后，就会有每一页的大纲，大家可以根据的自己的需求去调整页面顺序（不建议），自定义每一个页面的内容（这个很建议）

![示例2](./images/example-2.png)

#### 首先生成的是封面页

![示例3](./images/example-3.png)

#### 然后稍等一会儿后，会生成后面的所有页面（这里是并发生成的所有页面（默认是15个），如果大家的API供应商无法支持高并发的话，记得要去改一下设置）

![示例4](./images/example-4.png)

---

## 🏗️ 技术架构

### 后端
- **语言**: Python 3.11+
- **框架**: Flask
- **AI 模型**:
  - Gemini 3 (文案生成)
  - 🍌Nano banana Pro (图片生成)
- **包管理**: uv

### 前端
- **框架**: Vue 3 + TypeScript
- **构建**: Vite
- **状态管理**: Pinia

---

## 📦 如何自己部署

> 后续考虑发docker版本的，目前还是需要麻烦一点。

### 前置要求
- Python 3.11+
- Node.js 18+
- pnpm
- uv

### 1. 克隆项目
```bash
git clone https://github.com/HisMax/RedInk.git
cd RedInk
```

### 2. 配置 API 服务

复制配置模板文件：
```bash
cp text_providers.yaml.example text_providers.yaml
cp image_providers.yaml.example image_providers.yaml
```

编辑配置文件，填入你的 API Key 和服务配置。也可以启动后在 Web 界面的**设置页面**进行配置。

### 3. 安装后端依赖
```bash
uv sync
```

### 4. 安装前端依赖
```bash
cd frontend
pnpm install
```

### 5. 启动服务

**启动后端:**
```bash
uv run python -m backend.app
```
访问: http://localhost:12398

**启动前端:**
```bash
cd frontend
pnpm dev
```
访问: http://localhost:5173

---

## 🎮 使用指南

### 基础使用
1. **输入主题**: 在首页输入想要创作的主题,如"如何在家做拿铁"
2. **生成大纲**: AI 自动生成 6-9 页的内容大纲
3. **编辑确认**: 可以编辑和调整每一页的描述
4. **生成图片**: 点击生成,实时查看进度
5. **下载使用**: 一键下载所有图片

### 进阶使用
- **上传参考图片**: 适合品牌方,保持品牌视觉风格
- **修改描述词**: 精确控制每一页的内容和构图
- **重新生成**: 对不满意的页面单独重新生成

---

## 🔧 配置说明

### 配置方式

项目支持两种配置方式：

1. **Web 界面配置（推荐）**：启动服务后，在设置页面可视化配置
2. **YAML 文件配置**：直接编辑配置文件

### 文本生成配置

配置文件: `text_providers.yaml`

```yaml
# 当前激活的服务商
active_provider: openai

providers:
  # OpenAI 官方或兼容接口
  openai:
    type: openai_compatible
    api_key: sk-xxxxxxxxxxxxxxxxxxxx
    base_url: https://api.openai.com/v1
    model: gpt-4o

  # Google Gemini（原生接口）
  gemini:
    type: google_gemini
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-2.0-flash
```

### 图片生成配置

配置文件: `image_providers.yaml`

```yaml
# 当前激活的服务商
active_provider: gemini

providers:
  # Google Gemini 图片生成
  gemini:
    type: google_genai
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-3-pro-image-preview
    high_concurrency: false  # 高并发模式

  # OpenAI 兼容接口
  openai_image:
    type: image_api
    api_key: sk-xxxxxxxxxxxxxxxxxxxx
    base_url: https://your-api-endpoint.com
    model: dall-e-3
    high_concurrency: false
```

### 高并发模式说明

- **关闭（默认）**：图片逐张生成，适合 GCP 300$ 试用账号或有速率限制的 API
- **开启**：图片并行生成（最多15张同时），速度更快，但需要 API 支持高并发

⚠️ **GCP 300$ 试用账号不建议启用高并发**，可能会触发速率限制导致生成失败。

---

## ⚠️ 注意事项

1. **API 配额限制**:
   - 注意 Gemini 和图片生成 API 的调用配额
   - GCP 试用账号建议关闭高并发模式

2. **生成时间**:
   - 图片生成需要时间,请耐心等待（不要离开页面）

---

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request!

如果这个项目对你有帮助,欢迎给个 Star ⭐

### 未来计划
- [ ] 支持更多图片格式，例如一句话生成一套PPT什么的
- [ ] 历史记录管理优化
- [ ] 导出为各种格式(PDF、长图等)

---

## 更新日志

### v1.2.0 (2025-11-26)
- ✨ 新增版权信息展示，所有页面显示开源协议和项目链接
- ✨ 优化图片重新生成功能，支持单张图片重绘
- ✨ 重新生成图片时保持风格一致，传递完整上下文（封面图、大纲、用户输入）
- ✨ 修复图片缓存问题，重新生成的图片立即刷新显示
- ✨ 统一文本生成客户端接口，支持 Google Gemini 和 OpenAI 兼容接口自动切换
- ✨ 新增 Web 界面配置功能，可视化管理 API 服务商
- ✨ 新增高并发模式开关，适配不同 API 配额
- ✨ API Key 脱敏显示，保护密钥安全
- ✨ 配置自动保存，修改即时生效
- 🔧 调整默认 max_output_tokens 为 8000，兼容更多模型限制
- 🔧 优化前端路由和页面布局，提升用户体验
- 🔧 简化配置文件结构，移除冗余参数
- 🔧 优化历史记录图片显示，使用缩略图节省带宽
- 🔧 历史记录重新生成时自动从文件系统加载封面图作为参考
- 🐛 修复 `store.updateImage` 方法缺失导致的重新生成失败问题
- 🐛 修复历史记录加载时图片 URL 拼接错误
- 🐛 修复下载功能中原图参数处理问题
- 🐛 修复图片加载 500 错误问题

---

## 交流讨论与赞助

- **GitHub Issues**: [https://github.com/HisMax/RedInk/issues](https://github.com/HisMax/RedInk/issues)

### 联系作者

- **Email**: histonemax@gmail.com
- **微信**: Histone2024（添加请注明来意）
- **GitHub**: [@HisMax](https://github.com/HisMax)

### 用爱发电，如果可以，请默子喝一杯☕️咖啡吧

<img src="images/coffee.jpg" alt="赞赏码" width="300"/>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=HisMax/RedInk&type=Date)](https://star-history.com/#HisMax/RedInk&Date)

---

## 📄 开源协议

### 个人使用 - CC BY-NC-SA 4.0

本项目采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 协议进行开源

**你可以自由地：**
- ✅ **个人使用** - 用于学习、研究、个人项目
- ✅ **分享** - 在任何媒介以任何形式复制、发行本作品
- ✅ **修改** - 修改、转换或以本作品为基础进行创作

**但需要遵守以下条款：**
- 📝 **署名** - 必须给出适当的署名，提供指向本协议的链接，同时标明是否对原始作品作了修改
- 🚫 **非商业性使用** - 不得将本作品用于商业目的
- 🔄 **相同方式共享** - 如果你修改、转换或以本作品为基础进行创作，你必须以相同的协议分发你的作品

### 商业授权

如果你希望将本项目用于**商业目的**（包括但不限于）：
- 提供付费服务
- 集成到商业产品
- 作为 SaaS 服务运营
- 其他盈利性用途

**请联系作者获取商业授权：**
- 📧 Email: histonemax@gmail.com
- 💬 微信: Histone2024（请注明"商业授权咨询"）

默子会根据你的具体使用场景提供灵活的商业授权方案。

---

### 免责声明

本软件按"原样"提供，不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途的适用性和非侵权性的担保。在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责。

---

## 🙏 致谢

- [Google Gemini](https://ai.google.dev/) - 强大的文案生成能力
- 图片生成服务提供商 - 惊艳的图片生成效果
- [Linux.do](https://linux.do/) - 优秀的开发者社区

---

## 👨‍💻 作者

**默子 (Histone)** - AI 创业者 | Python & 深度学习

- 🏠 位置: 中国杭州
- 🚀 状态: 创业中
- 💡 专注: Transformers、GANs、多模态AI
- 📧 Email: histonemax@gmail.com
- 💬 微信: Histone2024
- 🐙 GitHub: [@HisMax](https://github.com/HisMax)

*"让 AI 帮我们做更有创造力的事"*

---

**如果这个项目帮到了你,欢迎分享给更多人!** ⭐

有任何问题或建议,欢迎提 Issue 或者在 Linux.do 原帖讨论!
