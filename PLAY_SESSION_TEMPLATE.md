# Play Session Template / 共同游玩模板

Use this when an AI player starts or resumes a Fox River Valley session with a human.

## Opening

```text
我会陪你慢慢玩，不会一次性通关。
我每回合最多执行 1-2 条命令，并在有选择时停下来问你。
先确认观战页已经打开，再决定开局模式。

你想用哪种开局？
A. solo：new_game("seed")
B. 自定义家庭：new_game("seed", companion_name="Alex", companion_profile="default")
C. Silas/Yaya demo：new_game("12071008", companion_name="Yaya", companion_profile="silas_yaya")
```

## First Turn

```text
当前理解：
我还没有替你选择模式。Yaya 是 Silas/Yaya demo，不是默认路线。

下一步意图：
先确认观战页和开局模式，再进入狐狸河谷。

执行命令：
cmd("runtime")
cmd("observer")

结果解释：
说明 runtime root、observer URL、观战页是否已经可用。

给玩家的选择：
A. solo
B. 自定义家庭，玩家给 companion 名字 / profile / family_species
C. Silas/Yaya demo
```

## Mid-session Save

```text
当前理解：
今天已经做了几件事，先把状态存住，避免丢脚印。

执行命令：
cmd("save")

结果解释：
说明保存成功，并提醒下次可用 load / recap 恢复。

给玩家的选择：
A. 继续玩一回合
B. 回家总结
C. 暂停
```

## Returning Home Summary

```text
回家总结：
- 今天去了哪里
- 获得了什么
- 家 / companion / kit 有什么变化
- 下一次可以做的 2-3 件小事

提醒：
不许一次性通关。除非你明确说“你自己玩”，我会停下来等你的选择。
```

## Speedrun Warning

如果自己发现正在连续跑命令，立刻停下，说：

```text
我刚才有点像在 speedrun。这里应该停下来让你选下一步。
```
