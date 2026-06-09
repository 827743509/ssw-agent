# blog-cli 命令参考

## 命令运行方式

全局安装后：

```bash
blog-cli <command>
```

在源码目录中：

```bash
npm run cli -- <command>
```

示例：

```bash
npm run cli -- post list
```

## 帮助

```bash
blog-cli --help
blog-cli post --help
blog-cli post create --help
blog-cli post update --help
blog-cli post delete --help
```

## 后端地址

持久设置后端地址：

```bash
blog-cli config set-base-url http://localhost:8080
```

查看当前配置：

```bash
blog-cli config show
```

临时指定后端地址：

```bash
blog-cli --base-url http://localhost:8080 post list
```

## 登录

推荐浏览器登录：

```bash
blog-cli login-browser
```

指定前端地址：

```bash
blog-cli login-browser --front-url http://127.0.0.1:5173
```

如果 CLI 版本支持账号密码登录：

```bash
blog-cli login --username admin --password 123456
```

查看当前用户：

```bash
blog-cli me
```

退出登录：

```bash
blog-cli logout
```

## 查看文章

公开文章：

```bash
blog-cli post list
```

我的文章：

```bash
blog-cli post mine
```

## 新增文章

直接传正文：

```bash
blog-cli post create --title "第一篇博客" --content "这是博客正文" --summary "这是摘要" --status 1 --tags "Java,Spring"
```

从文件读取正文：

```bash
blog-cli post create --title "第一篇博客" --content-file ./post.md --summary "这是摘要" --status 1 --tags "Java,Spring"
```

参数说明：

- `--title`：标题，必填。
- `--content`：正文，和 `--content-file` 二选一。
- `--content-file`：正文文件路径，和 `--content` 二选一。
- `--summary`：摘要，可选。
- `--status`：状态，可选；`0` 为草稿，`1` 为发布。
- `--tags`：标签，可选；多个标签用英文逗号分隔。

## 修改文章

```bash
blog-cli post update 1 --title "更新后的标题" --content "更新后的正文" --summary "更新后的摘要" --status 1 --tags "Java,MyBatis"
```

从文件读取正文：

```bash
blog-cli post update 1 --title "更新后的标题" --content-file ./post.md --summary "更新后的摘要" --status 1 --tags "Java,MyBatis"
```

## 删除文章

需要交互确认：

```bash
blog-cli post delete 1
```

跳过确认：

```bash
blog-cli post delete 1 --yes
```

只有用户已经明确确认删除时，Agent 才能使用 `--yes`。

## 常见失败处理

- `command not found`：说明 `blog-cli` 未全局安装；进入源码目录用 `npm run cli -- <command>`。
- 提示未登录：执行 `blog-cli login-browser` 或当前版本支持的 `blog-cli login`。
- 无法连接后端：检查后端服务是否启动，或用 `config set-base-url` 设置正确后端地址。
- 浏览器登录无响应：确认前端服务已启动，并用 `--front-url` 指定正确地址。
- 删除或修改失败：用 `post mine` 确认文章 ID 是否属于当前登录用户。
