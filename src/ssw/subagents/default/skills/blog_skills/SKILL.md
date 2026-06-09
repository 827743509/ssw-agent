---
name: blog-cli
description: 当 Agent 需要通过 blog-cli 管理博客系统时使用，包括登录、浏览器登录、获取当前用户、配置后端地址、查看文章、新增文章、修改文章、删除文章，以及处理本地 token 和常见 CLI 错误。
---

# 博客系统 Skill

## 用途

当 Agent 需要通过 `blog-cli` 管理博客系统时使用本 skill，包括登录、获取当前用户、查看文章、新增文章、修改文章、删除文章、配置后端地址，以及通过浏览器登录获取 token。

本 skill 是通用 Agent 操作说明，不绑定某个项目目录，也不要求安装到特定 Agent 框架中。

## 前置条件

- 本机已安装 Node.js。
- 已能访问博客后端服务。
- 已安装 `blog-cli`，或者可以定位到包含 `package.json` 的 `blog-cli` 源码目录。
- 如果使用浏览器登录，前端登录页必须可访问。

## 定位 CLI

优先直接执行：

```bash
blog-cli --help
```

如果系统找不到 `blog-cli`，询问用户 CLI 源码目录。进入源码目录后使用：

```bash
npm install
npm run cli -- --help
```

后续所有全局命令都可以改写成源码目录形式：

```bash
npm run cli -- <command>
```

例如：

```bash
npm run cli -- post list
```

## 基本流程

1. 检查 CLI 是否可用：`blog-cli --help`。
2. 如果后端不是默认地址，先设置后端地址：`blog-cli config set-base-url <后端地址>`。
3. 登录：
   - 推荐使用 `blog-cli login-browser`。
   - 如果当前 CLI 版本支持账号密码登录，也可以使用 `blog-cli login --username <用户名> --password <密码>`。
4. 登录后用 `blog-cli me` 检查当前用户。
5. 按用户请求执行文章查看、新增、修改或删除。

## 登录和 Token

`blog-cli` 登录成功后通常会把 token 保存到用户目录配置文件，例如：

```text
~/.blog-cli/config.json
```

Agent 不要把 token 输出到最终回答、日志或文档中。需要确认登录状态时，优先使用：

浏览器登录命令：

```bash
blog-cli login-browser
```

如果前端地址不是默认地址，使用：

```bash
blog-cli login-browser --front-url <前端地址>
```

如果后端地址不是默认地址，优先先配置：

```bash
blog-cli config set-base-url <后端地址>
```

也可以在支持全局参数的版本中临时传入：

```bash
blog-cli --base-url <后端地址> login-browser
```

## 文章操作

查看公开文章：

```bash
blog-cli post list
```

查看当前登录用户的文章：

```bash
blog-cli post mine
```

新增文章：

```bash
blog-cli post create --title "<标题>" --content "<正文>" --summary "<摘要>" --status 1 --tags "标签1,标签2"
```

从文件读取正文：

```bash
blog-cli post create --title "<标题>" --content-file <正文文件路径> --status 1 --tags "标签1,标签2"
```

修改文章：

```bash
blog-cli post update <文章ID> --title "<标题>" --content "<正文>" --summary "<摘要>" --status 1 --tags "标签1,标签2"
```

删除文章：

```bash
blog-cli post delete <文章ID>
```

如果用户已经明确确认删除，可使用：

```bash
blog-cli post delete <文章ID> --yes
```

## 安全规则

- 不要泄露 token。
- 不要把密码写入文档、提交记录或最终回答。
- 删除文章前确认用户意图；没有明确确认时不要使用 `--yes`。
- 新增或修改文章前确认标题、正文、发布状态和标签是否符合用户意图。
- 命令失败时优先读取错误信息，不要盲目重试破坏性操作。

## 命令参考

常用命令和参数详见 `references/commands.md`。当任务涉及具体命令参数、文件正文、浏览器登录或错误处理时，先读取该参考文件。
