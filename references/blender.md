# 用 Blender 拍一段音乐

在本 Skill 里，Blender 负责舞台、材质、灯光、摄影机、角色与道具的动作。项目里的歌曲时间轴负责决定何时进入哪个镜头，以及何时显示哪一句原歌词。叙事片和歌词视觉都可以选 Blender。

## 从样片开始

安装 Blender 4.5 LTS，准备好项目首页列出的 Node.js、Python、FFmpeg 依赖。从仓库根目录运行：

```sh
npm ci
python3 examples/night-train/make_audio.py
node render/cli.mjs examples/blender-station/project.json outputs/rail.png --start 5 --width 960 --height 540
node render/cli.mjs examples/blender-station/project.json outputs/rail.mp4 --width 960 --height 540 --fps 24
```

命令会查找 PATH 里的 `blender`，在 macOS 还会查找系统和个人 Applications 目录。自定义安装可将环境变量 `BLENDER_BIN` 指向可执行文件。打开 [雨后末班车的 .blend 工程](../examples/blender-station/rain-station.blend)，切换到摄影机视图并播放时间轴，可直接看三台摄影机的剪接。调整模型位置或镜头关键帧后保存，再运行相同命令即可。

## 以镜头为单位建模

- **叙事型 MV**。先说清这段歌里谁做了什么，以及镜头结束时什么已经改变。《雨后末班车》用车头接近、车窗掠过和长凳上的红外套讲离开。建立轨距、月台高度和轮对接触点，列车才有重量；摄影机是否移动，取决于观众要看车的速度、车内灯光还是留下的衣服。
- **歌词视觉 MV**。把一句歌词译成空间中可看见的变化。要表达“不同步”，可以让两根秒针从同一刻度出发，按不同速度转动，把第一次明显错开的位置剪在唱出关键词的附近。含义、镜号和场记均保留在工程里，两只表盘可以只用刻度。
- **人物连续动作**。需要让手接住衣服时，建立手和衣领的接触点，分别定伸手、承重、松手的姿态。用宽景检查两个人的站位，用近景检查手指是否穿模。相机变化也要留住原来运动的方向感。
- **色光与材质**。一个可控的颜色变化要能指出光源。钢轨吃到车头灯的暖反射，棚下的衣服吃到侧面的钨丝灯，远山保留冷色。出小样前抽看切点两侧与动作极值，检查皮肤、衣料、拉丝金属和透明材质在运动中是否稳定。

## 接入自己制作的场景

先在 Blender 内建立渲染摄影机，设定原生帧率和时间轴。多个机位可以绑定在不同时间标记上。把需要的模型、材质、纹理随工程保存；使用外部纹理或链接资源时，在 Blender 内打包可打包的资源，并保持其余资源的相对路径。

```sh
python3 scripts/new_project.py "/path/song.wav" "/path/my-mv" --style blender --mode narrative --blend "/path/to/shot.blend"
```

`project.json` 中可以整首使用 `style: "blender"`，也可以只在某一镜指定。每镜用 `blend` 引用相对路径，`firstFrame` 指定该镜在 Blender 源工程的起始帧，默认 1。`start`、`end` 沿用歌曲的绝对秒数。下面这段把歌曲第 8 至 12 秒接到源工程的第 97 帧开始处。

```json
{"start": 8, "end": 12, "style": "blender", "blend": "assets/shot-01.blend", "firstFrame": 97}
```

渲染器以源工程的每秒帧数映射到歌曲时间；改变导出的 fps 仍保持相同的播放速度。初始化工程会把第一镜铺到歌曲结尾；如果源动画较短，请在最后一个有效动作处切镜，再接下一镜。场景决定灯光、动画和颜色，最终的歌词与原唱采用统一的时间轴。材质中嵌入的招牌、纹理上的字符要在建模阶段清理。针对一处反馈，可以在同一条命令上加 `--start 8 --duration 2`，只检查该片段。

## 从代码重建三维工程

公开样片直接附带可编辑的 .blend。需要改变建模逻辑时，进入相应示例目录阅读 Python 源码。下面的命令在仓库根目录运行。macOS 的个人应用目录安装可以把开头的 `blender` 换成 `"$HOME/Applications/Blender.app/Contents/MacOS/Blender"`。

```sh
blender --background --factory-startup --python-exit-code 1 --python examples/blender-station/build.py -- --output outputs/custom-station.blend
```

[Blender 官方下载](https://www.blender.org/download/) · [后台渲染文档](https://docs.blender.org/manual/en/4.5/advanced/command_line/render.html)
