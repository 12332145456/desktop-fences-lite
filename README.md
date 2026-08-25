# Desktop Fences Lite v6

一个面向 Windows 的轻量桌面分区工具，以半透明分类面板展示个人桌面和公共桌面中的快捷方式、文件与文件夹。

## 安全边界

- 只扫描并显示桌面项目
- 不移动、不重命名、不删除桌面文件
- 面板准备完成后隐藏 Windows 原生桌面图标，退出时恢复
- 如果隐藏原生图标失败，程序会关闭分类面板，避免重复图标或空白桌面

## 功能

- 11 个默认分类，沿用 v3 的分类与布局风格
- 扫描个人桌面和公共桌面
- 每 5 秒自动发现新增或移除的桌面项目
- 显示真实 Windows 图标
- 分区内容支持滚轮浏览
- 拖动标题栏调整分区位置并自动保存
- 右键项目可手动修改显示分类
- 支持恢复默认布局、将当前布局设为默认
- 支持当前用户登录 Windows 后自动启动
- 双击项目可正常打开，面板之外不拦截其他程序的点击

## 直接运行

下载 `dist/desktop_fences_lite_v6.exe`，双击运行，或者双击：

```text
run_desktop_fences_lite.bat
```

右键任意分区标题可以刷新、管理布局、设置开机启动或退出。

也可以使用：

```text
enable_desktop_fences_startup.bat
disable_desktop_fences_startup.bat
```

## 从源码运行

需要 Windows 和 Python 3：

```powershell
python .\desktop_fences_lite.py
```

查看扫描与分类结果但不打开面板：

```powershell
python .\desktop_fences_lite.py --inventory
```

## 构建 EXE

```powershell
.\build_exe.ps1
```

脚本会在需要时安装 PyInstaller，然后生成：

```text
dist\desktop_fences_lite_v6.exe
```

## 屏幕截图是效果预览


```text
F8BE5E228BFDDD6BFFF90B2BBD56683FC2F1853FF0948D459FF2EBC8F5677222
```

