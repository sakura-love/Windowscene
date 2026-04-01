# Windows 情景模式

一个面向 Windows 的桌面情景模式软件。
开机后弹出“本次开机做什么”的情景选择窗口，根据用户当前要做的事情组织推荐应用，并由用户自己勾选本次真正要启动的软件。

当前版本基于 `PySide6` 构建，界面风格偏向 Windows 11，支持单文件 `exe` 分发。

## 仓库信息

- GitHub: `https://github.com/sakura-love/Windowscene`
- License: `MIT`
- 平台: `Windows`
- 技术栈: `Python 3` + `PySide6`

## 当前功能

- 支持开机自启动
- 支持开机后弹出情景模式选择
- 支持情景模式：游戏、视频、音乐、阅读、上网、编程、工作
- 支持手动配置每个情景的应用候选项
- 配置的应用仅作为可选项，不会默认全部自动启动
- 支持推荐应用卡片勾选后再启动
- 支持全盘扫描和指定位置扫描应用
- 支持首次扫描后本地缓存结果
- 支持分类化常见应用和游戏规则库
- 支持 `.url`、`.exe`、`.lnk` 等类型的图标兜底识别

## 下载与使用

如果你只是想使用软件，直接下载 Release 中的 `Windowscene.exe` 即可。

当前发布版已经支持单文件分发：

- 用户只需要下载一个 `exe`
- 默认配置会在首次运行时自动初始化
- 后续情景配置会由程序自动保存

## 界面预览

### 主界面

![Windowscene 主界面](screenshots/main.png)

## 本地开发

### 安装依赖

```powershell
cd E:\AIwork\Windowscene-GitHub
pip install -r requirements.txt
```

### 运行

```powershell
cd E:\AIwork\Windowscene-GitHub
python app.py
```

### 打包

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Windowscene --icon app_icon.ico app.py
```

## 项目结构

```text
app.py
qt_app.py
known_apps.json
requirements.txt
app_icon.ico
LICENSE
RELEASE_TEMPLATE.md
```

## 配置说明

程序运行时会维护这些数据：

- `scene_config.json`：用户自己的情景配置
- `known_apps.json`：常见应用与游戏分类规则
- `app_scan_cache.json`：扫描后的本地缓存

打包后的正式版会自动处理这些文件，普通用户不需要手动准备。

## v1.2.1 更新

- 调整配置与规则文件读取逻辑，支持程序首次运行时自动生成默认配置
- 优化打包后的资源加载方式，支持单 `exe` 分发
- 修正任务栏图标与窗口图标初始化逻辑
- 重整右侧信息栏与快捷操作区布局，减少默认窗口大小下的堆叠问题
- 补强 `.url` 快捷方式与部分 `.exe` 的图标获取逻辑
- 扩充常见应用与游戏分类规则库

## 后续方向

- 继续提升 `.lnk`、`.url`、`.exe` 图标提取成功率
- 增加更完整的 Windows 已安装应用识别
- 增加托盘常驻
- 增加系统动作，例如音量、电源模式、勿扰模式
