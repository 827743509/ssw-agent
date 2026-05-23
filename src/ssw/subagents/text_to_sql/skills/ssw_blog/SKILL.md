---
name: ssw_blog
description: ssw_blog项目的表结构，用于生成查询 SQL。
metadata:
  database_type: MySQL
---

## 表清单

| 表名 | 中文名 | 用途 |
| --- | --- | --- |
| `categories` | 文章分类表 | 保存文章分类，用于首页导航、筛选和文章归类。 |
| `tags` | 文章标签表 | 保存文章标签，用于按技术主题聚合文章。 |
| `articles` | 博客文章表 | 保存文章标题、摘要、正文、发布状态、发布时间等核心内容。 |
| `article_tags` | 文章标签关联表 | 保存文章和标签的多对多关系。 |

## `categories` 文章分类表

| 字段名 | 类型 | 是否为空 | 默认值 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增 | 主键 | 分类 ID。 |
| `name` | `VARCHAR(64)` | 否 | 无 | 唯一 | 分类名称。 |
| `description` | `VARCHAR(255)` | 是 | `NULL` | 无 | 分类描述。 |
| `created_at` | `DATETIME` | 否 | `CURRENT_TIMESTAMP` | 无 | 创建时间。 |

## `tags` 文章标签表

| 字段名 | 类型 | 是否为空 | 默认值 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增 | 主键 | 标签 ID。 |
| `name` | `VARCHAR(64)` | 否 | 无 | 唯一 | 标签名称。 |
| `created_at` | `DATETIME` | 否 | `CURRENT_TIMESTAMP` | 无 | 创建时间。 |

## `articles` 博客文章表

| 字段名 | 类型 | 是否为空 | 默认值 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `id` | `BIGINT` | 否 | 自增 | 主键 | 文章 ID。 |
| `category_id` | `BIGINT` | 否 | 无 | 无 | 所属分类 ID，逻辑关联 `categories.id`。 |
| `title` | `VARCHAR(160)` | 否 | 无 | 无 | 文章标题。 |
| `summary` | `VARCHAR(500)` | 否 | 无 | 无 | 文章摘要。 |
| `cover_url` | `VARCHAR(500)` | 是 | `NULL` | 无 | 封面图片地址。 |
| `content_md` | `MEDIUMTEXT` | 否 | 无 | 无 | Markdown 格式正文。 |
| `status` | `VARCHAR(20)` | 否 | `'PUBLISHED'` | 无 | 发布状态。当前查询只展示 `PUBLISHED` 状态文章。 |
| `view_count` | `BIGINT` | 否 | `0` | 无 | 浏览次数。 |
| `published_at` | `DATETIME` | 否 | `CURRENT_TIMESTAMP` | 无 | 发布时间。 |
| `created_at` | `DATETIME` | 否 | `CURRENT_TIMESTAMP` | 无 | 创建时间。 |
| `updated_at` | `DATETIME` | 否 | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 无 | 更新时间。 |

## `article_tags` 文章标签关联表

| 字段名 | 类型 | 是否为空 | 默认值 | 约束 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `article_id` | `BIGINT` | 否 | 无 | 联合主键 | 文章 ID，逻辑关联 `articles.id`。 |
| `tag_id` | `BIGINT` | 否 | 无 | 联合主键 | 标签 ID，逻辑关联 `tags.id`。 |

联合主键：`(article_id, tag_id)`，用于避免同一篇文章重复绑定同一个标签。

## 逻辑关联关系

| 关系 | 类型 | 关联字段 | 说明 |
| --- | --- | --- | --- |
| 分类 -> 文章 | 一对多 | `categories.id = articles.category_id` | 一个分类可以包含多篇文章；一篇文章归属一个分类。 |
| 文章 -> 标签 | 多对多 | `articles.id = article_tags.article_id`，`tags.id = article_tags.tag_id` | 一篇文章可以有多个标签；一个标签可以关联多篇文章。 |
