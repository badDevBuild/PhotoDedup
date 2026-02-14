# 3 万张照片，我只用了 10 分钟就挑完了

每次旅拍回来，最痛苦的不是修图，而是**选片**。

上周从云南回来，拍了将近两千张。加上电脑里之前积攒的几万张，全堆在一起。连拍的、重复的、废掉的——占了一大半。粗算了一下，这些"废片"吃掉了**几十 GB** 的硬盘空间。

一张张对比？我试过，眼都花了。

## Lightroom 解决不了的问题

Lightroom 是修图神器，但说到"批量找出重复照片并删掉"这件事，它真帮不了什么忙。

你只能自己翻，自己比，自己删。

翻到后面，根本记不清前面选了什么。连拍 10 张里面挑 1 张，光这件事就能耗掉一整个晚上。

## 所以我做了一个工具

**PhotoDedup**——一个专门给摄影师用的重复照片清理工具。

它做的事情很简单：

> **自动把长得像的照片放在一起，告诉你哪些该留、哪些可以删。**

不需要你一张张翻。不需要你记住哪些已经在 Lightroom 里修过了。它全都帮你搞定。

## 10 分钟，搞定几万张照片

### 第一步：选个文件夹

打开 PhotoDedup，选择你的照片文件夹，点"开始扫描"。就这么简单。

![选择文件夹，点击开始](https://raw.githubusercontent.com/badDevBuild/PhotoDedup/main/screenshots/2.png)

### 第二步：等它跑完

它会自动扫描所有 RAW 和 JPG，找出哪些照片长得像，把它们分成一组一组。

![扫描中，进度一目了然](https://raw.githubusercontent.com/badDevBuild/PhotoDedup/main/screenshots/4.png)

### 第三步：看看推荐方案

这是最让我惊喜的部分。

它不只是告诉你"这几张很像"——它会**自动推荐保留哪些**：

- 在 Lightroom 里编辑过的 → ✅ 保留
- 打了星的 → ✅ 保留
- 没编辑过的连拍重复 → ❌ 建议删除

比如我的云南照片文件夹，489 张里它建议保留 129 张，删掉 360 张，一下子腾出 **4.92 GB** 空间。整个硬盘清理下来，释放的空间还要多得多。

![推荐方案一览](https://raw.githubusercontent.com/badDevBuild/PhotoDedup/main/screenshots/1.png)

### 第四步：不放心？逐组检查

你可以一组一组翻看。绿框是留的，红框是删的。不同意？点一下就能改。

已经在 Lightroom 里编辑过的照片会有醒目的「已编辑」标签，一眼就能认出来。

![逐组审核，绿留红删](https://raw.githubusercontent.com/badDevBuild/PhotoDedup/main/screenshots/5.png)

### 第五步：一键清理

确认之后，点一下就全部清理干净。**所有照片是移入回收站的**，不是永久删除——反悔了随时恢复。

![清理完成，空间回来了](https://raw.githubusercontent.com/badDevBuild/PhotoDedup/main/screenshots/3.png)

## 它怎么知道我编辑过哪些照片？

很多朋友问我这个问题。

答案很简单：Lightroom 每次编辑一张照片，都会在旁边生成一个 `.xmp` 小文件。PhotoDedup 就是通过检测这个文件来判断的——**不需要你告诉它 Lightroom 目录在哪，全自动。**

## 免费、开源，谁都能用

PhotoDedup 是完全免费的，代码开源在 GitHub 上。

目前已在 macOS 上测试通过，Windows 和 Linux 版本也在适配中。

👉 **https://github.com/badDevBuild/PhotoDedup**

如果你不懂代码，找一个会写程序的朋友帮你装一下就行，5 分钟的事。

---

**如果你也受够了每次旅拍回来花一整晚选片删片，试试这个工具。**

**它不会帮你拍出好照片，但至少能帮你把废片清干净。**

*觉得有用的话，帮忙转发给你的摄影师朋友吧 📸*
