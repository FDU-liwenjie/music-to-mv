# 首页作品画面

这三张静帧取自项目作者此前制作的 MV，用于展示三种视觉语言。

| 画面 | 作品 | 镜头 |
| --- | --- | --- |
| [像素场景](fuji-pixel.jpg) | 《富士山下》像素版 | 雪山下的街道与相遇的两人 |
| [孔版印刷](summer-riso.jpg) | 《去年夏天（DJ 旋律氛围版）》孔版印刷版 | 暖纸、套色人物与悬挂的心形海报 |
| [水彩笔刷](summer-watercolor.jpg) | 同一首《去年夏天》的水彩版 | 女孩走近邮箱，信封飞出 |

《去年夏天》原有工程的画面由项目作者另作，孔版印刷方法与水彩笔刷实现参考了 [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)。音乐、字体与上游工具各有自己的授权。此前三支 MV 在首页以静帧展示，歌曲可由使用者自行导入。

## 两种拍法的可运行示例

[《雨站》](rain-station.gif) 与 [《两种时间》](out-of-time.gif) 各 12 秒，都以仓库中可重建的原创器乐小样为时间基准。这两个网页动图为静音循环预览。运行工程可以导出带音乐的 MP4。

- [《雨站》工程](../examples/rain-station/project.json) 包含三个剪纸镜头。雪夜站台的人物、红外套、列车和雨丝可分别移动。
- [《两种时间》工程](../examples/out-of-time/project.json) 以五句原创情绪短文演示歌词视觉。弹簧的张力、双手之间的印章和两只钟的转速分别表现文字含义。

```sh
python3 examples/night-train/make_audio.py
node render/cli.mjs examples/rain-station/project.json outputs/rain-station.mp4
node render/cli.mjs examples/out-of-time/project.json outputs/out-of-time.mp4
```
