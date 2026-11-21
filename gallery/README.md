# 首页作品画面

这三张静帧取自项目作者此前制作的 MV，用于展示三种视觉语言。

| 画面 | 作品 | 镜头 |
| --- | --- | --- |
| [像素场景](fuji-pixel.jpg) | 《富士山下》像素版 | 雪山下的街道与相遇的两人 |
| [孔版印刷](summer-riso.jpg) | 《去年夏天（DJ 旋律氛围版）》孔版印刷版 | 暖纸、套色人物与悬挂的心形海报 |
| [水彩笔刷](summer-watercolor.jpg) | 同一首《去年夏天》的水彩版 | 女孩走近邮箱，信封飞出 |

《去年夏天》原有工程的画面由项目作者另作，孔版印刷方法与水彩笔刷实现参考了 [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)。音乐、字体与上游工具各有自己的授权。此前三支 MV 在首页以静帧展示，歌曲可由使用者自行导入。

## 两种拍法的可运行示例

[《雨站》](rain-station.gif) 与 [《两种时间》](out-of-time.gif) 都以仓库中可重建的原创器乐小样为时间基准。每支动图长 12 秒，画幅为 480 × 270，以每秒 8 帧静音循环。运行工程可导出带音乐的 MP4。

- [《雨站》剪纸工程](../examples/rain-station/project.json) 包含三个镜头。两个人在站台等车，红外套从一只手递向另一只，一列火车驶入两人之间。新版动图的站牌以箭头指路。
- [《两种时间》工程](../examples/out-of-time/project.json) 在五个镜头里把情绪画成动作。弹簧受压、心形印章转手、飞鸟逃离，最后两只钟走向不同的时间。新版动图移除了装饰性省略号，钟面用指针和刻度表示时间。

两份工程将创作意图保存在分镜的 `meaning` 字段中。两支动图均已用空歌词时间轴重新渲染，全片以图像叙述。

```sh
python3 examples/night-train/make_audio.py
node render/cli.mjs examples/rain-station/project.json outputs/rain-station.mp4
node render/cli.mjs examples/out-of-time/project.json outputs/out-of-time.mp4
```

### 摄影版《雨站》

[预览](rain-cinema.webp) · [可编辑工程](../examples/rain-cinema/)。摄影式关键帧由 AI 生成。站台底板、带透明遮片的车体、灯影和掠过的窗框分别运动，公开工程配可重建的原创练习曲。
