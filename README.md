# deepin-code-replication-checker
check https://cr.deepin.io replication to gitlab, github, etc.

代码同步检测机器人（目前仅适用于deepin），特点如下：
- 每两个小时（可以在 [jenkins](https://ci.deepin.io) 上配置）执行一次检测
- 检测结果为不同步时，会发送提醒到bc的[代码推送检测](https://deepin.bearychat.com/inbox/代码推送检测)讨论组

## 检测结果为不同步的一般修复方式
一般是gerrit的replication队列卡住了（可能是有人没有使用规范的方式私自创建了gerrit项目导致），使用
```shell
# 请把 choldrim 换成你的用户名
# 使用这个可以看任务队列
ssh choldrim@cr.deepin.io -p 29418 ps -w

# 如果出现不同步的项目为：it/docker-services
ssh choldrim@cr.deepin.io -p 29418 replication start it/docker-services
```

## replication log
排查问题很多时候会用到gerrit的replication日志，位置在对应server的：`${gerrit_home}/logs/replication_log`
