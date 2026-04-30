# luogu-api-python API Reference

本文档由 `scripts/generate_api_docs.py` 从源码生成，覆盖公开 API 方法、参数、返回类型和 `pyLuogu.types` 中的数据结构定义域。

## 目录

- 同步方法：174 个
- 异步方法：174 个
- 类型：140 个
- 静态查看器：[api_viewer.html](api_viewer.html)

## 使用约定

- `luoguAPI` 是同步客户端。
- `asyncLuoguAPI` 是异步客户端，方法面与同步客户端保持一致，调用时需要 `await`。
- `RawDataResponse.data` 保存暂未细化结构的原始响应。
- 标记为 `unimplemented` 的方法是预留便捷方法，不代表已探测端点缺失。

## 同步 API: luoguAPI

### Activity

#### `delete_activity`

删除动态。这是同步方法。

- 状态：`implemented`
- 签名：`delete_activity(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_activity`

获取动态。这是同步方法。

- 状态：`implemented`
- 签名：`get_activity(uid: int, page: int | None = None) -> ActivityRequestResponse`
- 返回：`ActivityRequestResponse`
- 路由/端点引用：`ACTIVITY_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_watching_activities`

获取关注用户的动态。这是同步方法。

- 状态：`implemented`
- 签名：`get_watching_activities(page: int | None = None) -> ActivityRequestResponse`
- 返回：`ActivityRequestResponse`
- 路由/端点引用：`feed_watching`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `report_activity`

举报动态。这是同步方法。

- 状态：`implemented`
- 签名：`report_activity(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

### Article

#### `batch_update_articles`

批量更新文章。这是同步方法。

- 状态：`implemented`
- 签名：`batch_update_articles(request: BatchEditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_batch_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `BatchEditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `create_article`

创建文章。这是同步方法。

- 状态：`implemented`
- 签名：`create_article(request: EditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_article`

删除文章。这是同步方法。

- 状态：`implemented`
- 签名：`delete_article(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `delete_article_reply`

删除文章回复。这是同步方法。

- 状态：`implemented`
- 签名：`delete_article_reply(lid: int | str, id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_delete_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `favor_article`

收藏/取消收藏文章。这是同步方法。

- 状态：`implemented`
- 签名：`favor_article(lid: int | str, undo: bool | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_favor`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `undo` | `bool | None` | 否 | `None` | 是否撤销操作。 |

#### `find_article`

调用文章。这是同步方法。

- 状态：`implemented`
- 签名：`find_article(keyword: str, page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_find`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | `str` | 是 | `` | 搜索关键字。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_article`

获取文章。这是同步方法。

- 状态：`implemented`
- 签名：`get_article(lid: str) -> ArticleDataRequestResponse`
- 返回：`ArticleDataRequestResponse`
- 路由/端点引用：`article_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `str` | 是 | `` | 文章 ID。 |

#### `get_article_available_collections`

获取文章可用合集。这是同步方法。

- 状态：`implemented`
- 签名：`get_article_available_collections(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_available_collection`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `get_article_collection`

获取文章合集。这是同步方法。

- 状态：`implemented`
- 签名：`get_article_collection(id: int | str, page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_collection`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_article_list`

获取文章。这是同步方法。

- 状态：`implemented`
- 签名：`get_article_list(page: int | None = None, keyword: str | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_article_replies`

获取文章回复。这是同步方法。

- 状态：`implemented`
- 签名：`get_article_replies(lid: int | str, page: int | None = None) -> ArticleReplyListResponse`
- 返回：`ArticleReplyListResponse`
- 路由/端点引用：`article_replies`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_favored_articles`

获取favored文章。这是同步方法。

- 状态：`implemented`
- 签名：`get_favored_articles(page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_favored`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_my_articles`

获取我的文章。这是同步方法。

- 状态：`implemented`
- 签名：`get_my_articles(page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_mine`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `reply_article`

回复文章。这是同步方法。

- 状态：`implemented`
- 签名：`reply_article(lid: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `request_article_promotion`

请求文章promotion。这是同步方法。

- 状态：`implemented`
- 签名：`request_article_promotion(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_request_promotion`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `update_article`

更新文章。这是同步方法。

- 状态：`implemented`
- 签名：`update_article(lid: int | str, request: EditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `request` | `EditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `vote_article`

投票/评价文章。这是同步方法。

- 状态：`implemented`
- 签名：`vote_article(lid: int | str, vote: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_vote`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `vote` | `int` | 是 | `` | 投票值。 |

#### `withdraw_article_promotion`

撤回文章promotion。这是同步方法。

- 状态：`implemented`
- 签名：`withdraw_article_promotion(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_withdraw_promotion`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

### Auth

#### `auth_with_motp`

使用凭据完成邮件/手机验证码。这是同步方法。

- 状态：`implemented`
- 签名：`auth_with_motp(code: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |

#### `auth_with_password`

使用凭据完成password。这是同步方法。

- 状态：`implemented`
- 签名：`auth_with_password(username: str, password: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_password`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `username` | `str` | 是 | `` | 用户名。 |
| `password` | `str` | 是 | `` | 密码。 |

#### `auth_with_totp`

使用凭据完成totp。这是同步方法。

- 状态：`implemented`
- 签名：`auth_with_totp(code: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_totp`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |

#### `finish_signup`

完成signup。这是同步方法。

- 状态：`implemented`
- 签名：`finish_signup(request: RegisterRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_finish_signup`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `RegisterRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `get_lg4_captcha`

获取lg4验证码。这是同步方法。

- 状态：`implemented`
- 签名：`get_lg4_captcha() -> bytes`
- 返回：`bytes`
- 路由/端点引用：`captcha_lg4`
- 参数：无

#### `get_motp_target`

获取邮件/手机验证码target。这是同步方法。

- 状态：`implemented`
- 签名：`get_motp_target() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp_to`
- 参数：无

#### `lock_auth`

锁定认证。这是同步方法。

- 状态：`implemented`
- 签名：`lock_auth() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_lock`
- 参数：无

#### `login`

登录login的预留便捷方法，当前尚未实现。这是同步方法。

- 状态：`unimplemented`
- 签名：`login(user_name: str, password: str, captcha: Literal['input', 'ocr'], two_step_verify: Literal['google', 'email'] | None = None) -> bool`
- 返回：`bool`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user_name` | `str` | 是 | `` | 用户名。 |
| `password` | `str` | 是 | `` | 密码。 |
| `captcha` | `Literal['input', 'ocr']` | 是 | `` | 验证码处理方式或验证码文本。 |
| `two_step_verify` | `Literal['google', 'email'] | None` | 否 | `None` | 二步验证方式。 |

#### `logout`

登出logout。这是同步方法。

- 状态：`implemented`
- 签名：`logout() -> Any`
- 返回：`Any`
- 路由/端点引用：`auth_logout`
- 参数：无

#### `request_motp`

请求邮件/手机验证码。这是同步方法。

- 状态：`implemented`
- 签名：`request_motp() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp_request`
- 参数：无

#### `unlock_auth`

解锁认证。这是同步方法。

- 状态：`implemented`
- 签名：`unlock_auth(request: AuthUnlockRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_unlock`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `AuthUnlockRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

### Blog

#### `create_blog`

创建博客。这是同步方法。

- 状态：`implemented`
- 签名：`create_blog(request: EditBlogRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditBlogRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_blog`

删除博客。这是同步方法。

- 状态：`implemented`
- 签名：`delete_blog(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_blog`

获取博客。这是同步方法。

- 状态：`implemented`
- 签名：`get_blog(id: int | str) -> BlogDataRequestResponse`
- 返回：`BlogDataRequestResponse`
- 路由/端点引用：`blog_detail`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_blog_admin_list`

获取博客admin。这是同步方法。

- 状态：`implemented`
- 签名：`get_blog_admin_list(page_type: str | None = None, page: int | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_admin_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page_type` | `str | None` | 否 | `None` | 博客管理页类型。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_blog_list`

获取博客。这是同步方法。

- 状态：`implemented`
- 签名：`get_blog_list(page: int | None = None, keyword: str | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_lists`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_blog_replies`

获取博客回复。这是同步方法。

- 状态：`implemented`
- 签名：`get_blog_replies(id: int | str, page: int | None = None) -> BlogReplyListResponse`
- 返回：`BlogReplyListResponse`
- 路由/端点引用：`blog_replies`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `reply_blog`

回复博客。这是同步方法。

- 状态：`implemented`
- 签名：`reply_blog(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `update_blog`

更新博客。这是同步方法。

- 状态：`implemented`
- 签名：`update_blog(id: int | str, request: EditBlogRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditBlogRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_blog_admin_list`

更新博客admin。这是同步方法。

- 状态：`implemented`
- 签名：`update_blog_admin_list(form: BlogAdminForm, page_type: str | None = None) -> str`
- 返回：`str`
- 路由/端点引用：`blog_admin_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `form` | `BlogAdminForm` | 是 | `` | 表单请求体字典。 |
| `page_type` | `str | None` | 否 | `None` | 博客管理页类型。 |

#### `vote_blog`

投票/评价博客。这是同步方法。

- 状态：`implemented`
- 签名：`vote_blog(id: int | str, vote: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_vote`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `vote` | `int` | 是 | `` | 投票值。 |

### Chat

#### `clear_chat_unread`

清除私信unread。这是同步方法。

- 状态：`implemented`
- 签名：`clear_chat_unread(uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_clear_unread`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

#### `create_chat`

创建私信。这是同步方法。

- 状态：`implemented`
- 签名：`create_chat(uid: int, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `delete_chat`

删除私信。这是同步方法。

- 状态：`implemented`
- 签名：`delete_chat(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_chat_page`

获取私信。这是同步方法。

- 状态：`implemented`
- 签名：`get_chat_page() -> str`
- 返回：`str`
- 路由/端点引用：`chat`
- 参数：无

### Contest

#### `create_contest`

创建比赛。这是同步方法。

- 状态：`implemented`
- 签名：`create_contest(request: EditContestRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditContestRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_contest`

删除比赛。这是同步方法。

- 状态：`implemented`
- 签名：`delete_contest(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_contest`

获取比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_contest(id: int) -> ContestDataRequestResponse`
- 返回：`ContestDataRequestResponse`
- 路由/端点引用：`contest_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_contest_list`

获取比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_contest_list(page: int | None = None, name: str | None = None, method: int | None = None, public: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`CONTEST_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `name` | `str | None` | 否 | `None` | 名称过滤条件。 |
| `method` | `int | None` | 否 | `None` | 比赛赛制或 HTTP 方法，取决于上下文。 |
| `public` | `int | None` | 否 | `None` | 比赛公开分类。 |

#### `get_contest_scoreboard`

获取比赛排行榜。这是同步方法。

- 状态：`implemented`
- 签名：`get_contest_scoreboard(id: int | str, page: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_scoreboard`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_contest_squad`

获取比赛小队。这是同步方法。

- 状态：`implemented`
- 签名：`get_contest_squad(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_squad`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_contest`

获取创建的比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_created_contest(id: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_created`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_contest_list`

获取创建的比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_created_contest_list(page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`CREATED_CONTESTS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_joined_contest_list`

获取joined比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_joined_contest_list(page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`joined_contests`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_contest_list`

获取团队比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_contest_list(tid: int, page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`team_contests_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_contest_page`

获取团队比赛。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_contest_page(tid: int, page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`team_contest_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `join_contest`

加入比赛。这是同步方法。

- 状态：`implemented`
- 签名：`join_contest(id: int | str, request: ContestJoinRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_join`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `ContestJoinRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `quit_contest_squad_member`

调用比赛小队成员。这是同步方法。

- 状态：`implemented`
- 签名：`quit_contest_squad_member(id: int | str, uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_squad_member_quit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

#### `update_contest`

更新比赛。这是同步方法。

- 状态：`implemented`
- 签名：`update_contest(id: int | str, request: EditContestRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditContestRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### Discussion

#### `create_discussion`

创建讨论。这是同步方法。

- 状态：`implemented`
- 签名：`create_discussion(request: CreatePostRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_post`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `CreatePostRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_discussion`

删除讨论。这是同步方法。

- 状态：`implemented`
- 签名：`delete_discussion(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `delete_discussion_reply`

删除讨论回复。这是同步方法。

- 状态：`implemented`
- 签名：`delete_discussion_reply(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_delete_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_post_list`

获取创建的帖子。这是同步方法。

- 状态：`implemented`
- 签名：`get_created_post_list(page: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`created_posts`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_discussion_list`

获取讨论。这是同步方法。

- 状态：`implemented`
- 签名：`get_discussion_list(page: int | None = None, keyword: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_disscussion`

获取讨论。这是同步方法。

- 状态：`implemented`
- 签名：`get_disscussion(id: int, page: int | None = None, orderBy: int | None = None) -> DiscussionRequestResponse`
- 返回：`DiscussionRequestResponse`
- 路由/端点引用：`discussion_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `orderBy` | `int | None` | 否 | `None` | 排序字段。 |

#### `post_activity`

发布动态。这是同步方法。

- 状态：`implemented`
- 签名：`post_activity(content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_post`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `reply_discussion`

回复讨论。这是同步方法。

- 状态：`implemented`
- 签名：`reply_discussion(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `report_post`

举报帖子。这是同步方法。

- 状态：`implemented`
- 签名：`report_post(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`post_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

#### `report_post_reply`

举报帖子回复。这是同步方法。

- 状态：`implemented`
- 签名：`report_post_reply(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`post_reply_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

### Image

#### `delete_image`

删除图片。这是同步方法。

- 状态：`implemented`
- 签名：`delete_image(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`image_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `generate_image_upload_link`

生成图片uploadlink。这是同步方法。

- 状态：`implemented`
- 签名：`generate_image_upload_link(request: GenerateUploadLinkRequest | None = None) -> GenerateUploadLinkResponse`
- 返回：`GenerateUploadLinkResponse`
- 路由/端点引用：`image_generate_upload_link`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `GenerateUploadLinkRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `get_image`

获取图片。这是同步方法。

- 状态：`implemented`
- 签名：`get_image(id: int) -> Image`
- 返回：`Image`
- 路由/端点引用：`image_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_image_list`

获取图片。这是同步方法。

- 状态：`implemented`
- 签名：`get_image_list(page: int | None = None) -> ImageListRequestResponse`
- 返回：`ImageListRequestResponse`
- 路由/端点引用：`image_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

### Misc

#### `get_config`

获取配置。这是同步方法。

- 状态：`implemented`
- 签名：`get_config() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`config`
- 参数：无

#### `get_notifications`

获取notifications。这是同步方法。

- 状态：`implemented`
- 签名：`get_notifications(page: int | None = None) -> NotificationListRequestResponse`
- 返回：`NotificationListRequestResponse`
- 路由/端点引用：`notification`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_tags`

获取标签。这是同步方法。

- 状态：`implemented`
- 签名：`get_tags() -> TagRequestResponse`
- 返回：`TagRequestResponse`
- 路由/端点引用：`TAGS_ENDPOINT`
- 参数：无

### Other

#### `close`

关闭底层 HTTP 客户端。

- 状态：`implemented`
- 签名：`close() -> None`
- 返回：`None`
- 参数：无

#### `submit_ide_code`

提交idecode。这是同步方法。

- 状态：`implemented`
- 签名：`submit_ide_code(code: str, language: int, input_data: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`ide_submit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |
| `language` | `int` | 是 | `` | 语言编号。 |
| `input_data` | `str | None` | 否 | `None` | IDE 运行输入。 |

### Paintboard

#### `get_paintboard`

获取冬日绘板。这是同步方法。

- 状态：`implemented`
- 签名：`get_paintboard() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_board`
- 参数：无

#### `paint`

绘制paint。这是同步方法。

- 状态：`implemented`
- 签名：`paint(x: int, y: int, color: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_paint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `x` | `int` | 是 | `` | 绘板横坐标。 |
| `y` | `int` | 是 | `` | 绘板纵坐标。 |
| `color` | `int` | 是 | `` | 绘板颜色编号。 |

#### `reset_paintboard_token`

重置冬日绘板token。这是同步方法。

- 状态：`implemented`
- 签名：`reset_paintboard_token() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_reset_token`
- 参数：无

### Paste

#### `create_paste`

创建剪贴板。这是同步方法。

- 状态：`implemented`
- 签名：`create_paste(request: EditPasteRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditPasteRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_paste`

删除剪贴板。这是同步方法。

- 状态：`implemented`
- 签名：`delete_paste(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_paste`

获取剪贴板。这是同步方法。

- 状态：`implemented`
- 签名：`get_paste(id: str) -> PasteRequestResponse`
- 返回：`PasteRequestResponse`
- 路由/端点引用：`paste_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_paste_list`

获取剪贴板。这是同步方法。

- 状态：`implemented`
- 签名：`get_paste_list(page: int | None = None) -> PasteListRequestResponse`
- 返回：`PasteListRequestResponse`
- 路由/端点引用：`paste_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `update_paste`

更新剪贴板。这是同步方法。

- 状态：`implemented`
- 签名：`update_paste(id: int | str, request: EditPasteRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditPasteRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### Problem

#### `add_problem_to_tasklist`

添加题目tasklist。这是同步方法。

- 状态：`implemented`
- 签名：`add_problem_to_tasklist(pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_tasklist_add`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `add_training_problem`

添加题单题目。这是同步方法。

- 状态：`implemented`
- 签名：`add_training_problem(id: int | str, pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_add_problem`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `create_problem`

创建题目。这是同步方法。

- 状态：`implemented`
- 签名：`create_problem(settings: ProblemSettings, tid: int | None = None) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`PROBLEM_NEW_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `settings` | `ProblemSettings` | 是 | `` | 设置对象。 |
| `tid` | `int | None` | 否 | `None` | 团队 ID。 |

#### `delete_problem`

删除题目。这是同步方法。

- 状态：`implemented`
- 签名：`delete_problem(pid: str) -> bool`
- 返回：`bool`
- 路由/端点引用：`problem_delete_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `download_record_testcase`

下载评测记录测试点。这是同步方法。

- 状态：`implemented`
- 签名：`download_record_testcase(id: int | str, testcase: int | str | None = None) -> bytes`
- 返回：`bytes`
- 路由/端点引用：`record_download_testcase`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `testcase` | `int | str | None` | 否 | `None` | 测试点编号或名称。 |

#### `download_testcases`

下载测试点的预留便捷方法，当前尚未实现。这是同步方法。

- 状态：`unimplemented`
- 签名：`download_testcases(pid: int) -> Any`
- 返回：`Any`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `int` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_created_problem_list`

获取创建的题目。这是同步方法。

- 状态：`implemented`
- 签名：`get_created_problem_list(page: int | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`CREATED_PROBLEMS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_created_problem_set_list`

获取创建的题目set。这是同步方法。

- 状态：`implemented`
- 签名：`get_created_problem_set_list(page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`CREATED_PROBLEM_SETS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_problem`

获取题目。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem(pid: str, contest_id: int | None = None) -> ProblemDataRequestResponse`
- 返回：`ProblemDataRequestResponse`
- 路由/端点引用：`problem_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `contest_id` | `int | None` | 否 | `None` | 比赛 ID。 |

#### `get_problem_list`

获取题目。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_list(page: int | None = None, orderBy: str | None = None, order: Literal['asc', 'desc'] | None = None, keyword: str | None = None, content: bool | None = None, _type: Literal['P', 'U', 'T', 'B', 'CF', 'AT', 'UVA', 'SP'] | None = None, difficulty: int | None = None, tag: str | None = None, params: ProblemListRequestParams | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`PROBLEM_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `orderBy` | `str | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `content` | `bool | None` | 否 | `None` | 正文内容或是否请求正文，取决于方法。 |
| `_type` | `Literal['P', 'U', 'T', 'B', 'CF', 'AT', 'UVA', 'SP'] | None` | 否 | `None` | 题目类型过滤条件。 |
| `difficulty` | `int | None` | 否 | `None` | 题目难度过滤条件。 |
| `tag` | `str | None` | 否 | `None` | 标签过滤条件。 |
| `params` | `ProblemListRequestParams | None` | 否 | `None` | 已构造好的请求参数对象；传入后会覆盖同名便捷参数。 |

#### `get_problem_set`

获取题目set。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_set(id: int) -> ProblemSetDataRequestResponse`
- 返回：`ProblemSetDataRequestResponse`
- 路由/端点引用：`problem_set_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_problem_set_list`

获取题目set。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_set_list(page: int | None = None, keyword: str | None = None, type: Literal['official', 'select'] | None = None, params: ProblemSetListRequestParams | None = None) -> Any`
- 返回：`Any`
- 路由/端点引用：`PROBLEM_SET_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `type` | `Literal['official', 'select'] | None` | 否 | `None` | 接口参数。 |
| `params` | `ProblemSetListRequestParams | None` | 否 | `None` | 已构造好的请求参数对象；传入后会覆盖同名便捷参数。 |

#### `get_problem_settings`

获取题目设置。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_settings(pid: str) -> ProblemSettingsRequestResponse`
- 返回：`ProblemSettingsRequestResponse`
- 路由/端点引用：`problem_settings_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_problem_settings_legacy`

获取题目设置旧版。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_settings_legacy(pid: str) -> ProblemSettingsRequestResponse`
- 返回：`ProblemSettingsRequestResponse`
- 路由/端点引用：`problem_settings_legacy_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_problem_solutions`

获取题目solutions。这是同步方法。

- 状态：`implemented`
- 签名：`get_problem_solutions(pid: str, page: int | None = None) -> ProblemSolutionRequestResponse`
- 返回：`ProblemSolutionRequestResponse`
- 路由/端点引用：`problem_solution_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_problem_list`

获取团队题目。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_problem_list(tid: int, page: int | None = None, keyword: str | None = None, orderBy: Literal['pid', 'name'] | None = None, order: Literal['asc', 'desc'] | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`team_problems_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `orderBy` | `Literal['pid', 'name'] | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |

#### `get_team_problem_page`

获取团队题目。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_problem_page(tid: int, page: int | None = None, keyword: str | None = None, orderBy: Literal['pid', 'name'] | None = None, order: Literal['asc', 'desc'] | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`team_problem_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `orderBy` | `Literal['pid', 'name'] | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |

#### `get_team_problem_set_list`

获取团队题目set。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_problem_set_list(tid: int, page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`team_problem_sets_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `query_downloadable_testcase`

查询可下载测试点。这是同步方法。

- 状态：`implemented`
- 签名：`query_downloadable_testcase(id: int | str) -> DownloadableTestcaseResponse`
- 返回：`DownloadableTestcaseResponse`
- 路由/端点引用：`record_downloadable_testcase`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `remove_problem_from_tasklist`

移除题目tasklist。这是同步方法。

- 状态：`implemented`
- 签名：`remove_problem_from_tasklist(pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_tasklist_remove`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `submit_code`

提交code。这是同步方法。

- 状态：`implemented`
- 签名：`submit_code(pid: str, code: str, contest_id: int | None = None, lang: int | None = None, enableO2: bool | int = True, capture_handler: Callable[[<class 'bytes'>], str] | None = None) -> SubmitCodeResponse`
- 返回：`SubmitCodeResponse`
- 路由/端点引用：`problem_submit_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |
| `contest_id` | `int | None` | 否 | `None` | 比赛 ID。 |
| `lang` | `int | None` | 否 | `None` | 语言编号。 |
| `enableO2` | `bool | int` | 否 | `True` | 是否开启 O2 优化。 |
| `capture_handler` | `Callable[[<class 'bytes'>], str] | None` | 否 | `None` | 验证码回调函数。 |

#### `submit_code_via_openluogu`

提交codeopenluogu的预留便捷方法，当前尚未实现。这是同步方法。

- 状态：`unimplemented`
- 签名：`submit_code_via_openluogu() -> Any`
- 返回：`Any`
- 参数：无

#### `transfer_problem`

转移题目。这是同步方法。

- 状态：`implemented`
- 签名：`transfer_problem(pid: str, target: Literal['P', 'U', 'B'] | int = 'U', is_clone: bool = False) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`problem_transfer_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `target` | `Literal['P', 'U', 'B'] | int` | 否 | `'U'` | 转移目标；可以是题目归属类型或团队 ID。 |
| `is_clone` | `bool` | 否 | `False` | 是否克隆而非转移。 |

#### `translate_problem`

调用题目。这是同步方法。

- 状态：`implemented`
- 签名：`translate_problem(pid: str, request: TranslateProblemRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_translate`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `request` | `TranslateProblemRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_contest_problem`

更新比赛题目。这是同步方法。

- 状态：`implemented`
- 签名：`update_contest_problem(id: int | str, request: EditContestProblemRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_edit_problem`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditContestProblemRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_problem_settings`

更新题目设置。这是同步方法。

- 状态：`implemented`
- 签名：`update_problem_settings(pid: str, new_settings: ProblemSettings) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`problem_edit_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `new_settings` | `ProblemSettings` | 是 | `` | 新的设置对象。 |

#### `update_testcases_settings`

更新测试点设置。这是同步方法。

- 状态：`implemented`
- 签名：`update_testcases_settings(pid: str, new_settings: TestCaseSettings) -> UpdateTestCasesSettingsResponse`
- 返回：`UpdateTestCasesSettingsResponse`
- 路由/端点引用：`problem_edit_testcase_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `new_settings` | `TestCaseSettings` | 是 | `` | 新的设置对象。 |

#### `update_training_problems`

更新题单题目。这是同步方法。

- 状态：`implemented`
- 签名：`update_training_problems(id: int | str, request: EditTrainingProblemsRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_edit_problems`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTrainingProblemsRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `upload_testcases`

上传测试点的预留便捷方法，当前尚未实现。这是同步方法。

- 状态：`unimplemented`
- 签名：`upload_testcases(pid: int, path: str) -> Any`
- 返回：`Any`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `int` | 是 | `` | 题目编号，例如 P1000。 |
| `path` | `str` | 是 | `` | 本地文件路径。 |

### Ranking

#### `get_elo_ranking`

获取elo排名。这是同步方法。

- 状态：`implemented`
- 签名：`get_elo_ranking(page: int | None = None) -> RankingListRequestResponse`
- 返回：`RankingListRequestResponse`
- 路由/端点引用：`ranking_elo`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_ranking`

获取排名。这是同步方法。

- 状态：`implemented`
- 签名：`get_ranking(page: int | None = None) -> RankingListRequestResponse`
- 返回：`RankingListRequestResponse`
- 路由/端点引用：`ranking`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_rating_elo`

获取ratingelo。这是同步方法。

- 状态：`implemented`
- 签名：`get_rating_elo(uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`rating_elo`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

### Record

#### `get_chat_records`

获取私信records。这是同步方法。

- 状态：`implemented`
- 签名：`get_chat_records(user: int | None = None, page: int | None = None) -> ChatRecordRequestResponse`
- 返回：`ChatRecordRequestResponse`
- 路由/端点引用：`chat_record`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user` | `int | None` | 否 | `None` | 接口参数。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_record`

获取评测记录。这是同步方法。

- 状态：`implemented`
- 签名：`get_record(rid: str) -> RecordRequestResponse`
- 返回：`RecordRequestResponse`
- 路由/端点引用：`record_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `rid` | `str` | 是 | `` | 评测记录 ID。 |

#### `get_record_list`

获取评测记录。这是同步方法。

- 状态：`implemented`
- 签名：`get_record_list(page: int | None = None, uid: int | None = None) -> RecordListRequestResponse`
- 返回：`RecordListRequestResponse`
- 路由/端点引用：`record_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

### Team

#### `create_team`

创建团队。这是同步方法。

- 状态：`implemented`
- 签名：`create_team(request: EditTeamRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_create`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditTeamRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `exit_team`

退出团队。这是同步方法。

- 状态：`implemented`
- 签名：`exit_team(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_exit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_my_teams`

获取我的teams。这是同步方法。

- 状态：`implemented`
- 签名：`get_my_teams() -> TeamListRequestResponse`
- 返回：`TeamListRequestResponse`
- 路由/端点引用：`mine_team`
- 参数：无

#### `get_team`

获取团队。这是同步方法。

- 状态：`implemented`
- 签名：`get_team(tid: int) -> TeamDataRequestResponse`
- 返回：`TeamDataRequestResponse`
- 路由/端点引用：`team_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |

#### `join_team`

加入团队。这是同步方法。

- 状态：`implemented`
- 签名：`join_team(id: int | str, request: TeamJoinRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_join`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `TeamJoinRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `review_team_join_request`

审核团队joinrequest。这是同步方法。

- 状态：`implemented`
- 签名：`review_team_join_request(id: int | str, uid: int, accepted: bool) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_review`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `accepted` | `bool` | 是 | `` | 是否通过审核。 |

#### `set_team_master`

设置团队master。这是同步方法。

- 状态：`implemented`
- 签名：`set_team_master(id: int | str, uid: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_set_master`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `update_team`

更新团队。这是同步方法。

- 状态：`implemented`
- 签名：`update_team(id: int | str, request: EditTeamRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTeamRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_team_notice`

更新团队notice。这是同步方法。

- 状态：`implemented`
- 签名：`update_team_notice(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit_notice`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

### Training

#### `clone_training`

克隆题单。这是同步方法。

- 状态：`implemented`
- 签名：`clone_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_clone`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `create_training`

创建题单。这是同步方法。

- 状态：`implemented`
- 签名：`create_training(request: EditTrainingRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditTrainingRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_training`

删除题单。这是同步方法。

- 状态：`implemented`
- 签名：`delete_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_marked_training_list`

获取marked题单。这是同步方法。

- 状态：`implemented`
- 签名：`get_marked_training_list(page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`marked_trainings`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_training_page`

获取团队题单。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_training_page(tid: int, page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`team_training_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `mark_training`

标记题单。这是同步方法。

- 状态：`implemented`
- 签名：`mark_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_mark`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unmark_training`

取消标记题单。这是同步方法。

- 状态：`implemented`
- 签名：`unmark_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_unmark`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `update_training`

更新题单。这是同步方法。

- 状态：`implemented`
- 签名：`update_training(id: int | str, request: EditTrainingRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTrainingRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### User

#### `bind_openid`

绑定OpenID。这是同步方法。

- 状态：`implemented`
- 签名：`bind_openid(id: int | str, request: OpenIdAuthRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`openid_bind`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `OpenIdAuthRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `bind_vjudge_account`

绑定远程评测账号account。这是同步方法。

- 状态：`implemented`
- 签名：`bind_vjudge_account(request: BindRemoteJudgeAccountRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_bind_vjudge`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `BindRemoteJudgeAccountRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `connect_openid`

连接OpenID。这是同步方法。

- 状态：`implemented`
- 签名：`connect_openid(id: int | str, request: OpenIdAuthRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`openid_connect`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `OpenIdAuthRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `create_theme`

创建主题。这是同步方法。

- 状态：`implemented`
- 签名：`create_theme(request: EditThemeRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditThemeRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_blog_comment`

删除博客comment。这是同步方法。

- 状态：`implemented`
- 签名：`delete_blog_comment(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_delete_comment`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `delete_theme`

删除主题。这是同步方法。

- 状态：`implemented`
- 签名：`delete_theme(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_advertisement`

获取广告。这是同步方法。

- 状态：`implemented`
- 签名：`get_advertisement(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`advertisement`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_team_member_list`

获取团队成员。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_member_list(tid: int) -> TeamMemberRequestResponse`
- 返回：`TeamMemberRequestResponse`
- 路由/端点引用：`team_members_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |

#### `get_team_member_page`

获取团队成员。这是同步方法。

- 状态：`implemented`
- 签名：`get_team_member_page(tid: int, page: int | None = None) -> TeamMemberRequestResponse`
- 返回：`TeamMemberRequestResponse`
- 路由/端点引用：`team_member_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_theme_design`

获取主题design。这是同步方法。

- 状态：`implemented`
- 签名：`get_theme_design(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_design`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_theme_list`

获取主题。这是同步方法。

- 状态：`implemented`
- 签名：`get_theme_list(page: int | None = None) -> ThemeListRequestResponse`
- 返回：`ThemeListRequestResponse`
- 路由/端点引用：`theme_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user`

获取用户。这是同步方法。

- 状态：`implemented`
- 签名：`get_user(uid: int) -> UserDataRequestResponse`
- 返回：`UserDataRequestResponse`
- 路由/端点引用：`user_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_blacklist`

获取用户blacklist。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_blacklist(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_blacklist_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_blogs`

获取用户blogs。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_blogs(uid: int, page: int | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_user_blogs`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_follower_list`

获取用户粉丝。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_follower_list(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_followers_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_following_list`

获取用户关注。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_following_list(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_followings_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_info`

获取用户info。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_info(uid: int) -> UserDetails`
- 返回：`UserDetails`
- 路由/端点引用：`user_info_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_practice`

获取用户practice。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_practice(uid: int) -> UserPracticeResponse`
- 返回：`UserPracticeResponse`
- 路由/端点引用：`user_practice`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_preference`

获取用户偏好设置。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_preference() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_preference`
- 参数：无

#### `get_user_prize_setting`

获取用户prize设置。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_prize_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_prize_setting`
- 参数：无

#### `get_user_security_setting`

获取用户security设置。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_security_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_security_setting`
- 参数：无

#### `get_user_setting`

获取用户设置。这是同步方法。

- 状态：`implemented`
- 签名：`get_user_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_setting`
- 参数：无

#### `kick_team_member`

移除团队成员。这是同步方法。

- 状态：`implemented`
- 签名：`kick_team_member(id: int | str, uid: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_kick`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `me`

调用me。这是同步方法。

- 状态：`implemented`
- 签名：`me() -> UserDetails`
- 返回：`UserDetails`
- 参数：无

#### `search_user`

搜索用户。这是同步方法。

- 状态：`implemented`
- 签名：`search_user(keyword: str) -> list[UserSummary]`
- 返回：`list[UserSummary]`
- 路由/端点引用：`USER_SEARCH_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | `str` | 是 | `` | 搜索关键字。 |

#### `set_theme`

设置主题。这是同步方法。

- 状态：`implemented`
- 签名：`set_theme(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_set`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unbind_openid`

解绑OpenID。这是同步方法。

- 状态：`implemented`
- 签名：`unbind_openid(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_unbind_openid`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unbind_vjudge_account`

解绑远程评测账号account。这是同步方法。

- 状态：`implemented`
- 签名：`unbind_vjudge_account() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_unbind_vjudge`
- 参数：无

#### `update_team_member`

更新团队成员。这是同步方法。

- 状态：`implemented`
- 签名：`update_team_member(id: int | str, uid: int, request: TeamMemberUpdateRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit_member`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `request` | `TeamMemberUpdateRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_theme`

更新主题。这是同步方法。

- 状态：`implemented`
- 签名：`update_theme(id: int | str, request: EditThemeRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditThemeRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_user_header_image`

更新用户头图图片。这是同步方法。

- 状态：`implemented`
- 签名：`update_user_header_image(image: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_header_image`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `image` | `str` | 是 | `` | 图片 URL 或图片标识。 |

#### `update_user_introduction`

更新用户个人介绍。这是同步方法。

- 状态：`implemented`
- 签名：`update_user_introduction(introduction: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_introduction`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `introduction` | `str` | 是 | `` | 个人介绍内容。 |

#### `update_user_preference`

更新用户偏好设置。这是同步方法。

- 状态：`implemented`
- 签名：`update_user_preference(request: UserPreferenceUpdateRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_preference_update`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `UserPreferenceUpdateRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_user_slogan`

更新用户签名。这是同步方法。

- 状态：`implemented`
- 签名：`update_user_slogan(slogan: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_slogan`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `slogan` | `str` | 是 | `` | 用户签名。 |

## 异步 API: asyncLuoguAPI

### Activity

#### `delete_activity`

删除动态。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_activity(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_activity`

获取动态。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_activity(uid: int, page: int | None = None) -> ActivityRequestResponse`
- 返回：`ActivityRequestResponse`
- 路由/端点引用：`ACTIVITY_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_watching_activities`

获取关注用户的动态。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_watching_activities(page: int | None = None) -> ActivityRequestResponse`
- 返回：`ActivityRequestResponse`
- 路由/端点引用：`feed_watching`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `report_activity`

举报动态。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`report_activity(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

### Article

#### `batch_update_articles`

批量更新文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`batch_update_articles(request: BatchEditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_batch_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `BatchEditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `create_article`

创建文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_article(request: EditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_article`

删除文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_article(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `delete_article_reply`

删除文章回复。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_article_reply(lid: int | str, id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_delete_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `favor_article`

收藏/取消收藏文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`favor_article(lid: int | str, undo: bool | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_favor`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `undo` | `bool | None` | 否 | `None` | 是否撤销操作。 |

#### `find_article`

调用文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`find_article(keyword: str, page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_find`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | `str` | 是 | `` | 搜索关键字。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_article`

获取文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_article(lid: str) -> ArticleDataRequestResponse`
- 返回：`ArticleDataRequestResponse`
- 路由/端点引用：`article_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `str` | 是 | `` | 文章 ID。 |

#### `get_article_available_collections`

获取文章可用合集。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_article_available_collections(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_available_collection`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `get_article_collection`

获取文章合集。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_article_collection(id: int | str, page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_collection`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_article_list`

获取文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_article_list(page: int | None = None, keyword: str | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_article_replies`

获取文章回复。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_article_replies(lid: int | str, page: int | None = None) -> ArticleReplyListResponse`
- 返回：`ArticleReplyListResponse`
- 路由/端点引用：`article_replies`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_favored_articles`

获取favored文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_favored_articles(page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_favored`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_my_articles`

获取我的文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_my_articles(page: int | None = None) -> ArticleListRequestResponse`
- 返回：`ArticleListRequestResponse`
- 路由/端点引用：`article_mine`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `reply_article`

回复文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`reply_article(lid: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `request_article_promotion`

请求文章promotion。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`request_article_promotion(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_request_promotion`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

#### `update_article`

更新文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_article(lid: int | str, request: EditArticleRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `request` | `EditArticleRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `vote_article`

投票/评价文章。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`vote_article(lid: int | str, vote: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_vote`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |
| `vote` | `int` | 是 | `` | 投票值。 |

#### `withdraw_article_promotion`

撤回文章promotion。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`withdraw_article_promotion(lid: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`article_withdraw_promotion`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `lid` | `int | str` | 是 | `` | 文章 ID。 |

### Auth

#### `auth_with_motp`

使用凭据完成邮件/手机验证码。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`auth_with_motp(code: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |

#### `auth_with_password`

使用凭据完成password。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`auth_with_password(username: str, password: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_password`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `username` | `str` | 是 | `` | 用户名。 |
| `password` | `str` | 是 | `` | 密码。 |

#### `auth_with_totp`

使用凭据完成totp。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`auth_with_totp(code: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_totp`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |

#### `finish_signup`

完成signup。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`finish_signup(request: RegisterRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_finish_signup`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `RegisterRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `get_lg4_captcha`

获取lg4验证码。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_lg4_captcha() -> bytes`
- 返回：`bytes`
- 路由/端点引用：`captcha_lg4`
- 参数：无

#### `get_motp_target`

获取邮件/手机验证码target。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_motp_target() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp_to`
- 参数：无

#### `lock_auth`

锁定认证。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`lock_auth() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_lock`
- 参数：无

#### `login`

登录login的预留便捷方法，当前尚未实现。这是异步方法，需要 await。

- 状态：`unimplemented`
- 签名：`login(user_name: str, password: str, captcha: Literal['input', 'ocr'], two_step_verify: Literal['google', 'email'] | None = None) -> bool`
- 返回：`bool`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user_name` | `str` | 是 | `` | 用户名。 |
| `password` | `str` | 是 | `` | 密码。 |
| `captcha` | `Literal['input', 'ocr']` | 是 | `` | 验证码处理方式或验证码文本。 |
| `two_step_verify` | `Literal['google', 'email'] | None` | 否 | `None` | 二步验证方式。 |

#### `logout`

登出logout。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`logout() -> Any`
- 返回：`Any`
- 路由/端点引用：`auth_logout`
- 参数：无

#### `request_motp`

请求邮件/手机验证码。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`request_motp() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_motp_request`
- 参数：无

#### `unlock_auth`

解锁认证。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`unlock_auth(request: AuthUnlockRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`auth_unlock`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `AuthUnlockRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

### Blog

#### `create_blog`

创建博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_blog(request: EditBlogRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditBlogRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_blog`

删除博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_blog(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_blog`

获取博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_blog(id: int | str) -> BlogDataRequestResponse`
- 返回：`BlogDataRequestResponse`
- 路由/端点引用：`blog_detail`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_blog_admin_list`

获取博客admin。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_blog_admin_list(page_type: str | None = None, page: int | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_admin_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page_type` | `str | None` | 否 | `None` | 博客管理页类型。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_blog_list`

获取博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_blog_list(page: int | None = None, keyword: str | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_lists`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_blog_replies`

获取博客回复。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_blog_replies(id: int | str, page: int | None = None) -> BlogReplyListResponse`
- 返回：`BlogReplyListResponse`
- 路由/端点引用：`blog_replies`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `reply_blog`

回复博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`reply_blog(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `update_blog`

更新博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_blog(id: int | str, request: EditBlogRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditBlogRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_blog_admin_list`

更新博客admin。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_blog_admin_list(form: BlogAdminForm, page_type: str | None = None) -> str`
- 返回：`str`
- 路由/端点引用：`blog_admin_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `form` | `BlogAdminForm` | 是 | `` | 表单请求体字典。 |
| `page_type` | `str | None` | 否 | `None` | 博客管理页类型。 |

#### `vote_blog`

投票/评价博客。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`vote_blog(id: int | str, vote: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_vote`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `vote` | `int` | 是 | `` | 投票值。 |

### Chat

#### `clear_chat_unread`

清除私信unread。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`clear_chat_unread(uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_clear_unread`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

#### `create_chat`

创建私信。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_chat(uid: int, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `delete_chat`

删除私信。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_chat(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`chat_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_chat_page`

获取私信。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_chat_page() -> str`
- 返回：`str`
- 路由/端点引用：`chat`
- 参数：无

### Contest

#### `create_contest`

创建比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_contest(request: EditContestRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditContestRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_contest`

删除比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_contest(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_contest`

获取比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_contest(id: int) -> ContestDataRequestResponse`
- 返回：`ContestDataRequestResponse`
- 路由/端点引用：`contest_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_contest_list`

获取比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_contest_list(page: int | None = None, name: str | None = None, method: int | None = None, public: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`CONTEST_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `name` | `str | None` | 否 | `None` | 名称过滤条件。 |
| `method` | `int | None` | 否 | `None` | 比赛赛制或 HTTP 方法，取决于上下文。 |
| `public` | `int | None` | 否 | `None` | 比赛公开分类。 |

#### `get_contest_scoreboard`

获取比赛排行榜。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_contest_scoreboard(id: int | str, page: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_scoreboard`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_contest_squad`

获取比赛小队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_contest_squad(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_squad`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_contest`

获取创建的比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_created_contest(id: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_created`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_contest_list`

获取创建的比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_created_contest_list(page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`CREATED_CONTESTS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_joined_contest_list`

获取joined比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_joined_contest_list(page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`joined_contests`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_contest_list`

获取团队比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_contest_list(tid: int, page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`team_contests_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_contest_page`

获取团队比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_contest_page(tid: int, page: int | None = None) -> ContestListRequestResponse`
- 返回：`ContestListRequestResponse`
- 路由/端点引用：`team_contest_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `join_contest`

加入比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`join_contest(id: int | str, request: ContestJoinRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_join`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `ContestJoinRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `quit_contest_squad_member`

调用比赛小队成员。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`quit_contest_squad_member(id: int | str, uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_squad_member_quit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

#### `update_contest`

更新比赛。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_contest(id: int | str, request: EditContestRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditContestRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### Discussion

#### `create_discussion`

创建讨论。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_discussion(request: CreatePostRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_post`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `CreatePostRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_discussion`

删除讨论。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_discussion(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `delete_discussion_reply`

删除讨论回复。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_discussion_reply(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_delete_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_created_post_list`

获取创建的帖子。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_created_post_list(page: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`created_posts`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_discussion_list`

获取讨论。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_discussion_list(page: int | None = None, keyword: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |

#### `get_disscussion`

获取讨论。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_disscussion(id: int, page: int | None = None, orderBy: int | None = None) -> DiscussionRequestResponse`
- 返回：`DiscussionRequestResponse`
- 路由/端点引用：`discussion_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `orderBy` | `int | None` | 否 | `None` | 排序字段。 |

#### `post_activity`

发布动态。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`post_activity(content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`feed_post`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `reply_discussion`

回复讨论。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`reply_discussion(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`discuss_reply`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

#### `report_post`

举报帖子。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`report_post(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`post_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

#### `report_post_reply`

举报帖子回复。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`report_post_reply(id: int | str, reason: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`post_reply_report`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `reason` | `str | None` | 否 | `None` | 举报原因。 |

### Image

#### `delete_image`

删除图片。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_image(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`image_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `generate_image_upload_link`

生成图片uploadlink。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`generate_image_upload_link(request: GenerateUploadLinkRequest | None = None) -> GenerateUploadLinkResponse`
- 返回：`GenerateUploadLinkResponse`
- 路由/端点引用：`image_generate_upload_link`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `GenerateUploadLinkRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `get_image`

获取图片。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_image(id: int) -> Image`
- 返回：`Image`
- 路由/端点引用：`image_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_image_list`

获取图片。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_image_list(page: int | None = None) -> ImageListRequestResponse`
- 返回：`ImageListRequestResponse`
- 路由/端点引用：`image_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

### Misc

#### `get_config`

获取配置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_config() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`config`
- 参数：无

#### `get_notifications`

获取notifications。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_notifications(page: int | None = None) -> NotificationListRequestResponse`
- 返回：`NotificationListRequestResponse`
- 路由/端点引用：`notification`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_tags`

获取标签。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_tags() -> TagRequestResponse`
- 返回：`TagRequestResponse`
- 路由/端点引用：`TAGS_ENDPOINT`
- 参数：无

### Other

#### `aclose`

关闭底层 HTTP 客户端。

- 状态：`implemented`
- 签名：`aclose() -> None`
- 返回：`None`
- 参数：无

#### `submit_ide_code`

提交idecode。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`submit_ide_code(code: str, language: int, input_data: str | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`ide_submit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |
| `language` | `int` | 是 | `` | 语言编号。 |
| `input_data` | `str | None` | 否 | `None` | IDE 运行输入。 |

### Paintboard

#### `get_paintboard`

获取冬日绘板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_paintboard() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_board`
- 参数：无

#### `paint`

绘制paint。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`paint(x: int, y: int, color: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_paint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `x` | `int` | 是 | `` | 绘板横坐标。 |
| `y` | `int` | 是 | `` | 绘板纵坐标。 |
| `color` | `int` | 是 | `` | 绘板颜色编号。 |

#### `reset_paintboard_token`

重置冬日绘板token。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`reset_paintboard_token() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paintboard_reset_token`
- 参数：无

### Paste

#### `create_paste`

创建剪贴板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_paste(request: EditPasteRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditPasteRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_paste`

删除剪贴板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_paste(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_paste`

获取剪贴板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_paste(id: str) -> PasteRequestResponse`
- 返回：`PasteRequestResponse`
- 路由/端点引用：`paste_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_paste_list`

获取剪贴板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_paste_list(page: int | None = None) -> PasteListRequestResponse`
- 返回：`PasteListRequestResponse`
- 路由/端点引用：`paste_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `update_paste`

更新剪贴板。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_paste(id: int | str, request: EditPasteRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`paste_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditPasteRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### Problem

#### `add_problem_to_tasklist`

添加题目tasklist。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`add_problem_to_tasklist(pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_tasklist_add`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `add_training_problem`

添加题单题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`add_training_problem(id: int | str, pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_add_problem`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `create_problem`

创建题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_problem(settings: ProblemSettings, tid: int | None = None) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`PROBLEM_NEW_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `settings` | `ProblemSettings` | 是 | `` | 设置对象。 |
| `tid` | `int | None` | 否 | `None` | 团队 ID。 |

#### `delete_problem`

删除题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_problem(pid: str) -> bool`
- 返回：`bool`
- 路由/端点引用：`problem_delete_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `download_record_testcase`

下载评测记录测试点。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`download_record_testcase(id: int | str, testcase: int | str | None = None) -> bytes`
- 返回：`bytes`
- 路由/端点引用：`record_download_testcase`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `testcase` | `int | str | None` | 否 | `None` | 测试点编号或名称。 |

#### `download_testcases`

下载测试点的预留便捷方法，当前尚未实现。这是异步方法，需要 await。

- 状态：`unimplemented`
- 签名：`download_testcases(pid: int) -> Any`
- 返回：`Any`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `int` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_created_problem_list`

获取创建的题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_created_problem_list(page: int | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`CREATED_PROBLEMS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_created_problem_set_list`

获取创建的题目set。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_created_problem_set_list(page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`CREATED_PROBLEM_SETS_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_problem`

获取题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem(pid: str, contest_id: int | None = None) -> ProblemDataRequestResponse`
- 返回：`ProblemDataRequestResponse`
- 路由/端点引用：`problem_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `contest_id` | `int | None` | 否 | `None` | 比赛 ID。 |

#### `get_problem_list`

获取题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_list(page: int | None = None, orderBy: str | None = None, order: Literal['asc', 'desc'] | None = None, keyword: str | None = None, content: bool | None = None, _type: Literal['P', 'U', 'T', 'B', 'CF', 'AT', 'UVA', 'SP'] | None = None, difficulty: int | None = None, tag: str | None = None, params: ProblemListRequestParams | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`PROBLEM_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `orderBy` | `str | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `content` | `bool | None` | 否 | `None` | 正文内容或是否请求正文，取决于方法。 |
| `_type` | `Literal['P', 'U', 'T', 'B', 'CF', 'AT', 'UVA', 'SP'] | None` | 否 | `None` | 题目类型过滤条件。 |
| `difficulty` | `int | None` | 否 | `None` | 题目难度过滤条件。 |
| `tag` | `str | None` | 否 | `None` | 标签过滤条件。 |
| `params` | `ProblemListRequestParams | None` | 否 | `None` | 已构造好的请求参数对象；传入后会覆盖同名便捷参数。 |

#### `get_problem_set`

获取题目set。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_set(id: int) -> ProblemSetDataRequestResponse`
- 返回：`ProblemSetDataRequestResponse`
- 路由/端点引用：`problem_set_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_problem_set_list`

获取题目set。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_set_list(page: int | None = None, keyword: str | None = None, type: Literal['official', 'select'] | None = None, params: ProblemSetListRequestParams | None = None) -> Any`
- 返回：`Any`
- 路由/端点引用：`PROBLEM_SET_LIST_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `type` | `Literal['official', 'select'] | None` | 否 | `None` | 接口参数。 |
| `params` | `ProblemSetListRequestParams | None` | 否 | `None` | 已构造好的请求参数对象；传入后会覆盖同名便捷参数。 |

#### `get_problem_settings`

获取题目设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_settings(pid: str) -> ProblemSettingsRequestResponse`
- 返回：`ProblemSettingsRequestResponse`
- 路由/端点引用：`problem_settings_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_problem_settings_legacy`

获取题目设置旧版。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_settings_legacy(pid: str) -> ProblemSettingsRequestResponse`
- 返回：`ProblemSettingsRequestResponse`
- 路由/端点引用：`problem_settings_legacy_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `get_problem_solutions`

获取题目solutions。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_problem_solutions(pid: str, page: int | None = None) -> ProblemSolutionRequestResponse`
- 返回：`ProblemSolutionRequestResponse`
- 路由/端点引用：`problem_solution_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_problem_list`

获取团队题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_problem_list(tid: int, page: int | None = None, keyword: str | None = None, orderBy: Literal['pid', 'name'] | None = None, order: Literal['asc', 'desc'] | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`team_problems_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `orderBy` | `Literal['pid', 'name'] | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |

#### `get_team_problem_page`

获取团队题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_problem_page(tid: int, page: int | None = None, keyword: str | None = None, orderBy: Literal['pid', 'name'] | None = None, order: Literal['asc', 'desc'] | None = None) -> ProblemListRequestResponse`
- 返回：`ProblemListRequestResponse`
- 路由/端点引用：`team_problem_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `keyword` | `str | None` | 否 | `None` | 搜索关键字。 |
| `orderBy` | `Literal['pid', 'name'] | None` | 否 | `None` | 排序字段。 |
| `order` | `Literal['asc', 'desc'] | None` | 否 | `None` | 排序方向。 |

#### `get_team_problem_set_list`

获取团队题目set。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_problem_set_list(tid: int, page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`team_problem_sets_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `query_downloadable_testcase`

查询可下载测试点。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`query_downloadable_testcase(id: int | str) -> DownloadableTestcaseResponse`
- 返回：`DownloadableTestcaseResponse`
- 路由/端点引用：`record_downloadable_testcase`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `remove_problem_from_tasklist`

移除题目tasklist。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`remove_problem_from_tasklist(pid: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_tasklist_remove`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |

#### `submit_code`

提交code。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`submit_code(pid: str, code: str, contest_id: int | None = None, lang: int | None = None, enableO2: bool | int = True, capture_handler: Callable[[<class 'bytes'>, <class 'int'>], str] | None = None) -> SubmitCodeResponse`
- 返回：`SubmitCodeResponse`
- 路由/端点引用：`problem_submit_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `code` | `str` | 是 | `` | 验证码、TOTP/MOTP 码或提交代码，取决于方法。 |
| `contest_id` | `int | None` | 否 | `None` | 比赛 ID。 |
| `lang` | `int | None` | 否 | `None` | 语言编号。 |
| `enableO2` | `bool | int` | 否 | `True` | 是否开启 O2 优化。 |
| `capture_handler` | `Callable[[<class 'bytes'>, <class 'int'>], str] | None` | 否 | `None` | 验证码回调函数。 |

#### `submit_code_via_openluogu`

提交codeopenluogu的预留便捷方法，当前尚未实现。这是异步方法，需要 await。

- 状态：`unimplemented`
- 签名：`submit_code_via_openluogu() -> Any`
- 返回：`Any`
- 参数：无

#### `transfer_problem`

转移题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`transfer_problem(pid: str, target: Literal['P', 'U', 'B'] | int = 'U', is_clone: bool = False) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`problem_transfer_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `target` | `Literal['P', 'U', 'B'] | int` | 否 | `'U'` | 转移目标；可以是题目归属类型或团队 ID。 |
| `is_clone` | `bool` | 否 | `False` | 是否克隆而非转移。 |

#### `translate_problem`

调用题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`translate_problem(pid: str, request: TranslateProblemRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`problem_translate`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `request` | `TranslateProblemRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_contest_problem`

更新比赛题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_contest_problem(id: int | str, request: EditContestProblemRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`contest_edit_problem`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditContestProblemRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_problem_settings`

更新题目设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_problem_settings(pid: str, new_settings: ProblemSettings) -> ProblemModifiedResponse`
- 返回：`ProblemModifiedResponse`
- 路由/端点引用：`problem_edit_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `new_settings` | `ProblemSettings` | 是 | `` | 新的设置对象。 |

#### `update_testcases_settings`

更新测试点设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_testcases_settings(pid: str, new_settings: TestCaseSettings) -> UpdateTestCasesSettingsResponse`
- 返回：`UpdateTestCasesSettingsResponse`
- 路由/端点引用：`problem_edit_testcase_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `str` | 是 | `` | 题目编号，例如 P1000。 |
| `new_settings` | `TestCaseSettings` | 是 | `` | 新的设置对象。 |

#### `update_training_problems`

更新题单题目。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_training_problems(id: int | str, request: EditTrainingProblemsRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_edit_problems`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTrainingProblemsRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `upload_testcases`

上传测试点的预留便捷方法，当前尚未实现。这是异步方法，需要 await。

- 状态：`unimplemented`
- 签名：`upload_testcases(pid: int, path: str) -> Any`
- 返回：`Any`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pid` | `int` | 是 | `` | 题目编号，例如 P1000。 |
| `path` | `str` | 是 | `` | 本地文件路径。 |

### Ranking

#### `get_elo_ranking`

获取elo排名。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_elo_ranking(page: int | None = None) -> RankingListRequestResponse`
- 返回：`RankingListRequestResponse`
- 路由/端点引用：`ranking_elo`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_ranking`

获取排名。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_ranking(page: int | None = None) -> RankingListRequestResponse`
- 返回：`RankingListRequestResponse`
- 路由/端点引用：`ranking`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_rating_elo`

获取ratingelo。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_rating_elo(uid: int | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`rating_elo`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

### Record

#### `get_chat_records`

获取私信records。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_chat_records(user: int | None = None, page: int | None = None) -> ChatRecordRequestResponse`
- 返回：`ChatRecordRequestResponse`
- 路由/端点引用：`chat_record`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user` | `int | None` | 否 | `None` | 接口参数。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_record`

获取评测记录。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_record(rid: str) -> RecordRequestResponse`
- 返回：`RecordRequestResponse`
- 路由/端点引用：`record_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `rid` | `str` | 是 | `` | 评测记录 ID。 |

#### `get_record_list`

获取评测记录。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_record_list(page: int | None = None, uid: int | None = None) -> RecordListRequestResponse`
- 返回：`RecordListRequestResponse`
- 路由/端点引用：`record_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |
| `uid` | `int | None` | 否 | `None` | 用户 ID。 |

### Team

#### `create_team`

创建团队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_team(request: EditTeamRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_create`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditTeamRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `exit_team`

退出团队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`exit_team(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_exit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_my_teams`

获取我的teams。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_my_teams() -> TeamListRequestResponse`
- 返回：`TeamListRequestResponse`
- 路由/端点引用：`mine_team`
- 参数：无

#### `get_team`

获取团队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team(tid: int) -> TeamDataRequestResponse`
- 返回：`TeamDataRequestResponse`
- 路由/端点引用：`team_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |

#### `join_team`

加入团队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`join_team(id: int | str, request: TeamJoinRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_join`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `TeamJoinRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `review_team_join_request`

审核团队joinrequest。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`review_team_join_request(id: int | str, uid: int, accepted: bool) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_review`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `accepted` | `bool` | 是 | `` | 是否通过审核。 |

#### `set_team_master`

设置团队master。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`set_team_master(id: int | str, uid: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_set_master`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `update_team`

更新团队。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_team(id: int | str, request: EditTeamRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTeamRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_team_notice`

更新团队notice。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_team_notice(id: int | str, content: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit_notice`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `content` | `str` | 是 | `` | 正文内容或是否请求正文，取决于方法。 |

### Training

#### `clone_training`

克隆题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`clone_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_clone`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `create_training`

创建题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_training(request: EditTrainingRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditTrainingRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_training`

删除题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_marked_training_list`

获取marked题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_marked_training_list(page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`marked_trainings`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_team_training_page`

获取团队题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_training_page(tid: int, page: int | None = None) -> ProblemSetListRequestResponse`
- 返回：`ProblemSetListRequestResponse`
- 路由/端点引用：`team_training_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `mark_training`

标记题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`mark_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_mark`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unmark_training`

取消标记题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`unmark_training(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_unmark`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `update_training`

更新题单。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_training(id: int | str, request: EditTrainingRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`training_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditTrainingRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

### User

#### `bind_openid`

绑定OpenID。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`bind_openid(id: int | str, request: OpenIdAuthRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`openid_bind`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `OpenIdAuthRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `bind_vjudge_account`

绑定远程评测账号account。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`bind_vjudge_account(request: BindRemoteJudgeAccountRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_bind_vjudge`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `BindRemoteJudgeAccountRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `connect_openid`

连接OpenID。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`connect_openid(id: int | str, request: OpenIdAuthRequest | None = None) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`openid_connect`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `OpenIdAuthRequest | None` | 否 | `None` | 请求体对象；字段定义见对应 Request 类型。 |

#### `create_theme`

创建主题。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`create_theme(request: EditThemeRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_new`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `EditThemeRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `delete_blog_comment`

删除博客comment。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_blog_comment(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`blog_delete_comment`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `delete_theme`

删除主题。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`delete_theme(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_delete`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_advertisement`

获取广告。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_advertisement(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`advertisement`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_team_member_list`

获取团队成员。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_member_list(tid: int) -> TeamMemberRequestResponse`
- 返回：`TeamMemberRequestResponse`
- 路由/端点引用：`team_members_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |

#### `get_team_member_page`

获取团队成员。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_team_member_page(tid: int, page: int | None = None) -> TeamMemberRequestResponse`
- 返回：`TeamMemberRequestResponse`
- 路由/端点引用：`team_member_page`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tid` | `int` | 是 | `` | 团队 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_theme_design`

获取主题design。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_theme_design(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_design`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `get_theme_list`

获取主题。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_theme_list(page: int | None = None) -> ThemeListRequestResponse`
- 返回：`ThemeListRequestResponse`
- 路由/端点引用：`theme_list`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user`

获取用户。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user(uid: int) -> UserDataRequestResponse`
- 返回：`UserDataRequestResponse`
- 路由/端点引用：`user_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_blacklist`

获取用户blacklist。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_blacklist(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_blacklist_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_blogs`

获取用户blogs。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_blogs(uid: int, page: int | None = None) -> BlogListRequestResponse`
- 返回：`BlogListRequestResponse`
- 路由/端点引用：`blog_user_blogs`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_follower_list`

获取用户粉丝。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_follower_list(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_followers_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_following_list`

获取用户关注。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_following_list(uid: int, page: int | None = None) -> list[UserDetails]`
- 返回：`list[UserDetails]`
- 路由/端点引用：`user_followings_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `page` | `int | None` | 否 | `None` | 页码；为 None 时使用洛谷默认页。 |

#### `get_user_info`

获取用户info。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_info(uid: int) -> UserDetails`
- 返回：`UserDetails`
- 路由/端点引用：`user_info_endpoint`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_practice`

获取用户practice。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_practice(uid: int) -> UserPracticeResponse`
- 返回：`UserPracticeResponse`
- 路由/端点引用：`user_practice`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `get_user_preference`

获取用户偏好设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_preference() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_preference`
- 参数：无

#### `get_user_prize_setting`

获取用户prize设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_prize_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_prize_setting`
- 参数：无

#### `get_user_security_setting`

获取用户security设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_security_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_security_setting`
- 参数：无

#### `get_user_setting`

获取用户设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`get_user_setting() -> UserSettingResponse`
- 返回：`UserSettingResponse`
- 路由/端点引用：`user_setting`
- 参数：无

#### `kick_team_member`

移除团队成员。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`kick_team_member(id: int | str, uid: int) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_kick`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |

#### `me`

调用me。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`me() -> UserDetails`
- 返回：`UserDetails`
- 参数：无

#### `search_user`

搜索用户。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`search_user(keyword: str) -> list[UserSummary]`
- 返回：`list[UserSummary]`
- 路由/端点引用：`USER_SEARCH_ENDPOINT`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | `str` | 是 | `` | 搜索关键字。 |

#### `set_theme`

设置主题。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`set_theme(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_set`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unbind_openid`

解绑OpenID。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`unbind_openid(id: int | str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_unbind_openid`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |

#### `unbind_vjudge_account`

解绑远程评测账号account。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`unbind_vjudge_account() -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_unbind_vjudge`
- 参数：无

#### `update_team_member`

更新团队成员。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_team_member(id: int | str, uid: int, request: TeamMemberUpdateRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`team_edit_member`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `uid` | `int` | 是 | `` | 用户 ID。 |
| `request` | `TeamMemberUpdateRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_theme`

更新主题。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_theme(id: int | str, request: EditThemeRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`theme_edit`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `int | str` | 是 | `` | 资源 ID，具体含义由方法名决定。 |
| `request` | `EditThemeRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_user_header_image`

更新用户头图图片。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_user_header_image(image: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_header_image`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `image` | `str` | 是 | `` | 图片 URL 或图片标识。 |

#### `update_user_introduction`

更新用户个人介绍。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_user_introduction(introduction: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_introduction`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `introduction` | `str` | 是 | `` | 个人介绍内容。 |

#### `update_user_preference`

更新用户偏好设置。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_user_preference(request: UserPreferenceUpdateRequest) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_preference_update`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `request` | `UserPreferenceUpdateRequest` | 是 | `` | 请求体对象；字段定义见对应 Request 类型。 |

#### `update_user_slogan`

更新用户签名。这是异步方法，需要 await。

- 状态：`implemented`
- 签名：`update_user_slogan(slogan: str) -> RawDataResponse`
- 返回：`RawDataResponse`
- 路由/端点引用：`user_update_slogan`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `slogan` | `str` | 是 | `` | 用户签名。 |

## 类型定义域

### `LuoguType`

`LuoguType` 数据结构。

- 字段：无

### `RequestParams`

`RequestParams` 数据结构。

- 字段：无

### `Response`

`Response` 数据结构。

- 字段：无

### `PagedList`

`PagedList` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `results` | `list[T_of_list]` |
| `count` | `int` |
| `perPage` | `int` |

### `ListRequestParams`

`ListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `orderBy` | `int` |

### `ProblemListRequestParams`

`ProblemListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `orderBy` | `str` |
| `order` | `str` |
| `keyword` | `str` |
| `content` | `bool` |
| `type` | `str` |
| `difficulty` | `int` |
| `tag` | `str` |

### `ProblemSetListRequestParams`

`ProblemSetListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `keyword` | `str` |
| `type` | `str` |

### `ContestListRequestParams`

`ContestListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `name` | `str` |
| `method` | `int` |
| `public` | `int` |

### `TeamProblemListRequestParams`

`TeamProblemListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `keyword` | `str` |
| `orderBy` | `str` |
| `order` | `str` |

### `UserListRequestParams`

`UserListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `int` |
| `page` | `int` |
| `orderBy` | `int` |

### `RecordListRequestParams`

`RecordListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `pid` | `str` |
| `contestId` | `int` |
| `user` | `str` |
| `status` | `int` |
| `language` | `int` |
| `orderBy` | `int` |

### `ThemeListRequestParams`

`ThemeListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `orderBy` | `str` |
| `order` | `str` |
| `type` | `str` |

### `ArticleListRequestParams`

`ArticleListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `int` |
| `page` | `int` |
| `category` | `int` |
| `ascending` | `bool` |
| `promoted` | `bool` |
| `title` | `str` |

### `BlogListRequestParams`

`BlogListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `uid` | `int` |
| `keyword` | `str` |
| `type` | `str` |
| `page` | `int` |

### `RankingListRequestParams`

`RankingListRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `orderBy` | `int` |

### `ProblemRequestParams`

`ProblemRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `contestId` | `int` |

### `UserSearchRequestParams`

`UserSearchRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `keyword` | `str` |

### `DiscussionRequestParams`

`DiscussionRequestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `page` | `int` |
| `orderBy` | `int` |

### `ActivityReuqestParams`

`ActivityReuqestParams` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `int` |
| `page` | `int` |

### `ProblemSketch`

`ProblemSketch` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `pid` | `str` |
| `title` | `str` |
| `difficulty` | `int` |
| `type` | `str` |
| `submitted` | `bool` |
| `accepted` | `bool` |

### `ProblemSummary`

`ProblemSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `pid` | `str` |
| `title` | `str` |
| `difficulty` | `int` |
| `type` | `str` |
| `submitted` | `bool` |
| `accepted` | `bool` |
| `tags` | `list[int]` |
| `totalSubmit` | `int` |
| `totalAccepted` | `int` |
| `flag` | `int` |
| `fullScore` | `int` |

### `VjudgeSummary`

`VjudgeSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `origin` | `str` |
| `link` | `str` |
| `id` | `str` |

### `UserSummary`

`UserSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `uid` | `int` |
| `name` | `str` |
| `avatar` | `str` |
| `slogan` | `str` |
| `badge` | `str` |
| `isAdmin` | `bool` |
| `isBanned` | `bool` |
| `isRoot` | `bool` |
| `color` | `str` |
| `ccfLevel` | `int` |
| `xcpcLevel` | `int` |
| `background` | `str` |

### `TeamSummary`

`TeamSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `isPremium` | `bool` |

### `ProblemContent`

`ProblemContent` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `UserSummary` |
| `version` | `int` |
| `name` | `str` |
| `background` | `str` |
| `description` | `str` |
| `formatI` | `str` |
| `formatO` | `str` |
| `hint` | `str` |
| `locale` | `str` |

### `Group`

`Group` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `no` | `int` |

### `TeamMember`

`TeamMember` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `group` | `Group` |
| `user` | `UserSummary` |
| `type` | `int` |
| `permission` | `int` |
| `realName` | `str` |

### `Provider`

`Provider` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `UserSummary` |
| `team` | `TeamSummary` |

### `Attachment`

`Attachment` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `size` | `int` |
| `uploadTime` | `int` |
| `downloadLink` | `str` |
| `id` | `str` |
| `filename` | `str` |
| `fileName` | `str` |

### `ProblemSetSummary`

`ProblemSetSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `createTime` | `int` |
| `deadline` | `int` |
| `problemCount` | `int` |
| `marked` | `bool` |
| `markCount` | `int` |
| `id` | `int` |
| `name` | `str` |
| `title` | `str` |
| `type` | `int` |
| `provider` | `Provider` |

### `ContestSketch`

`ContestSketch` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `startTime` | `int` |
| `endTime` | `int` |

### `Forum`

`Forum` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `name` | `str` |
| `type` | `int` |
| `slug` | `str` |
| `color` | `str` |

### `Reply`

`Reply` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `content` | `str` |
| `time` | `int` |
| `author` | `UserSummary` |

### `PostSketch`

`PostSketch` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `title` | `str` |
| `author` | `UserSummary` |
| `time` | `int` |

### `PostSummary`

`PostSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `content` | `str` |
| `createTime` | `int` |
| `updateTime` | `int` |
| `forum` | `Forum` |
| `topped` | `bool` |
| `valid` | `bool` |
| `locked` | `bool` |
| `replyCount` | `int` |

### `Prize`

`Prize` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `year` | `int` |
| `contestName` | `str` |
| `prize` | `str` |

### `EloRatingSummary`

`EloRatingSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `contest` | `ContestSketch` |
| `rating` | `int` |
| `time` | `int` |
| `latest` | `bool` |

### `ProblemDetails`

`ProblemDetails` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `pid` | `str` |
| `title` | `str` |
| `difficulty` | `int` |
| `type` | `str` |
| `submitted` | `bool` |
| `accepted` | `bool` |
| `tags` | `list[int]` |
| `totalSubmit` | `int` |
| `totalAccepted` | `int` |
| `flag` | `int` |
| `fullScore` | `int` |
| `content` | `ProblemContent` |
| `samples` | `list[tuple[str, str]]` |
| `provider` | `Provider` |
| `attachments` | `list[Attachment]` |
| `limits` | `list[tuple[int, int]]` |
| `showScore` | `bool` |
| `score` | `int` |
| `stdCode` | `str` |
| `vjudge` | `VjudgeSummary` |
| `acceptLanguages` | `list[int]` |

### `TestCase`

`TestCase` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `upid` | `int` |
| `inputFileName` | `str` |
| `outputFileName` | `str` |
| `timeLimit` | `int` |
| `memoryLimit` | `int` |
| `fullScore` | `int` |
| `isPretest` | `bool` |
| `subtaskId` | `int` |

### `ScoringStrategy`

`ScoringStrategy` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `type` | `int` |
| `script` | `str` |

### `ProblemSettings`

`ProblemSettings` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `title` | `str` |
| `background` | `str` |
| `description` | `str` |
| `inputFormat` | `str` |
| `outputFormat` | `str` |
| `samples` | `list[tuple[str, str]]` |
| `hint` | `str` |
| `translation` | `str` |
| `comment` | `str` |
| `needsTranslation` | `bool` |
| `acceptSolution` | `bool` |
| `allowDataDownload` | `bool` |
| `tags` | `list[int]` |
| `difficulty` | `int` |
| `showScore` | `bool` |
| `providerID` | `int` |
| `flag` | `int` |

### `TestCaseSettings`

`TestCaseSettings` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `cases` | `list[TestCase]` |
| `subtaskScoringStrategies` | `dict[str, ScoringStrategy]` |
| `scoringStrategy` | `ScoringStrategy` |
| `showSubtask` | `bool` |

### `UserDetails`

`UserDetails` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `uid` | `int` |
| `name` | `str` |
| `avatar` | `str` |
| `slogan` | `str` |
| `badge` | `str` |
| `isAdmin` | `bool` |
| `isBanned` | `bool` |
| `isRoot` | `bool` |
| `color` | `str` |
| `ccfLevel` | `int` |
| `xcpcLevel` | `int` |
| `background` | `str` |
| `followingCount` | `int` |
| `followerCount` | `int` |
| `ranking` | `int` |
| `registerTime` | `int` |
| `introduction` | `str` |
| `prize` | `list[Prize]` |
| `elo` | `EloRatingSummary` |
| `eloMax` | `EloRatingSummary` |
| `userRelationship` | `int` |
| `reverseUserRelationship` | `int` |
| `passedProblemCount` | `int` |
| `submittedProblemCount` | `int` |

### `ProblemSetDetails`

`ProblemSetDetails` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `createTime` | `int` |
| `deadline` | `int` |
| `problemCount` | `int` |
| `marked` | `bool` |
| `markCount` | `int` |
| `id` | `int` |
| `name` | `str` |
| `title` | `str` |
| `type` | `int` |
| `provider` | `Provider` |
| `description` | `str` |
| `problems` | `list[ProblemSummary]` |

### `ContestSummary`

`ContestSummary` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `startTime` | `int` |
| `endTime` | `int` |
| `method` | `int` |
| `visibility` | `int` |
| `ruleType` | `int` |
| `visibilityType` | `int` |
| `invitationCodeType` | `int` |
| `rated` | `int` |
| `problemCount` | `int` |
| `host` | `Provider` |
| `squad` | `bool` |

### `ContestDetails`

`ContestDetails` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `startTime` | `int` |
| `endTime` | `int` |
| `method` | `int` |
| `visibility` | `int` |
| `ruleType` | `int` |
| `visibilityType` | `int` |
| `invitationCodeType` | `int` |
| `rated` | `int` |
| `problemCount` | `int` |
| `host` | `Provider` |
| `squad` | `bool` |
| `description` | `str` |
| `totalParticipants` | `int` |
| `eloThreshold` | `int` |
| `eloDone` | `bool` |
| `canEdit` | `bool` |
| `problems` | `list[ProblemSummary]` |
| `isScoreboardFrozen` | `bool` |

### `ContestSettings`

`ContestSettings` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `name` | `str` |
| `description` | `str` |
| `visibilityType` | `int` |
| `invitationCodeType` | `int` |
| `ruleType` | `int` |
| `startTime` | `int` |
| `endTime` | `int` |
| `rated` | `bool` |
| `ratingGroup` | `str` |
| `eloThreshold` | `int` |
| `eloCenter` | `int` |

### `Activity`

`Activity` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `content` | `str` |
| `id` | `int` |
| `type` | `int` |
| `time` | `int` |
| `user` | `UserSummary` |

### `TeamSettings`

`TeamSettings` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `description` | `str` |
| `notice` | `str` |
| `contact` | `dict[str, str]` |
| `joinPermission` | `int` |

### `TeamDetail`

`TeamDetail` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `isPremium` | `bool` |
| `createTime` | `int` |
| `master` | `UserSummary` |
| `setting` | `TeamSettings` |
| `premiumUntil` | `int` |
| `type` | `int` |
| `memberCount` | `int` |

### `Record`

`Record` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `time` | `int` |
| `memory` | `int` |
| `problem` | `ProblemSketch` |
| `contest` | `ContestSummary` |
| `sourceCodeLength` | `int` |
| `submitTime` | `int` |
| `language` | `int` |
| `user` | `UserSummary` |
| `id` | `int` |
| `status` | `int` |
| `enableO2` | `bool` |
| `score` | `int` |

### `TestCaseStatus`

`TestCaseStatus` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `status` | `int` |
| `time` | `int` |
| `memory` | `int` |
| `score` | `int` |
| `signal` | `int` |
| `exitCode` | `int` |
| `description` | `str` |
| `subtaskID` | `int` |

### `SubtaskStatus`

`SubtaskStatus` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `score` | `int` |
| `status` | `int` |
| `testCases` | `list[TestCaseStatus]` |
| `judger` | `str` |
| `time` | `int` |
| `memory` | `int` |

### `CompileResult`

`CompileResult` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `success` | `bool` |
| `message` | `str` |
| `opt2` | `bool` |

### `JudgeResult`

`JudgeResult` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `finishedCaseCount` | `int` |
| `status` | `int` |
| `time` | `int` |
| `memory` | `int` |
| `score` | `int` |

### `RecordStatus`

`RecordStatus` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `compileResult` | `CompileResult` |
| `judgeResult` | `JudgeResult` |
| `version` | `int` |

### `RecordDetails`

`RecordDetails` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `time` | `int` |
| `memory` | `int` |
| `problem` | `ProblemSketch` |
| `contest` | `ContestSummary` |
| `sourceCodeLength` | `int` |
| `submitTime` | `int` |
| `language` | `int` |
| `user` | `UserSummary` |
| `id` | `int` |
| `status` | `int` |
| `enableO2` | `bool` |
| `score` | `int` |
| `detail` | `RecordStatus` |
| `sourceCode` | `str` |

### `Post`

`Post` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `content` | `str` |
| `createTime` | `int` |
| `updateTime` | `int` |
| `forum` | `Forum` |
| `topped` | `bool` |
| `valid` | `bool` |
| `locked` | `bool` |
| `replyCount` | `int` |
| `pinnedReply` | `Reply` |

### `Paste`

`Paste` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `data` | `str` |
| `id` | `str` |
| `user` | `UserSummary` |
| `time` | `int` |
| `public` | `bool` |

### `Image`

`Image` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `thumbnailUrl` | `str` |
| `url` | `str` |
| `id` | `str` |
| `provider` | `UserSummary` |
| `uploadTime` | `int` |
| `size` | `int` |

### `Article`

`Article` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `lid` | `str` |
| `title` | `str` |
| `time` | `int` |
| `author` | `UserSummary` |
| `upvote` | `int` |
| `replyCount` | `int` |
| `favorCount` | `int` |
| `category` | `int` |
| `status` | `int` |
| `solutionFor` | `ProblemSketch` |
| `promoteStatus` | `int` |
| `content` | `str` |
| `categoryOld` | `str` |
| `contentFull` | `bool` |
| `adminNote` | `str` |
| `adminComment` | `str` |
| `voted` | `int` |
| `canReply` | `bool` |
| `canEdit` | `bool` |

### `TagDetail`

`TagDetail` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `type` | `int` |
| `parent` | `int` |

### `TagType`

`TagType` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `color` | `str` |

### `ProblemListRequestResponse`

`ProblemListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `problems` | `list[ProblemSummary]` |
| `count` | `int` |
| `perPage` | `int` |

### `ProblemSetListRequestResponse`

`ProblemSetListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `trainings` | `list[ProblemSetSummary]` |
| `count` | `int` |
| `perPage` | `int` |
| `page` | `int` |

### `ProblemDataRequestResponse`

`ProblemDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `problem` | `ProblemDetails` |
| `translations` | `dict[str, ProblemContent]` |
| `bookmarked` | `bool` |
| `contest` | `ContestSketch` |
| `vjudgeUsername` | `str` |
| `lastLanguage` | `int` |
| `lastCode` | `str` |
| `recommendations` | `list[ProblemSketch]` |
| `forum` | `Forum` |
| `discussions` | `list[PostSketch]` |
| `canEdit` | `bool` |

### `ProblemSettingsRequestResponse`

`ProblemSettingsRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `problemSettings` | `ProblemSettings` |
| `testCaseSettings` | `TestCaseSettings` |
| `isClonedTestCases` | `bool` |
| `updating` | `bool` |
| `testDataDownloadLink` | `str` |
| `isProblemAdmin` | `bool` |
| `privilegedTeams` | `list[TeamSummary]` |

### `ProblemModifiedResponse`

`ProblemModifiedResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `pid` | `str` |

### `UpdateTestCasesSettingsResponse`

`UpdateTestCasesSettingsResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `problem` | `ProblemDetails` |
| `testCases` | `list[TestCase]` |
| `scoringStrategy` | `ScoringStrategy` |
| `subtaskScoringStrategies` | `dict[str, ScoringStrategy]` |

### `ProblemSolutionRequestResponse`

`ProblemSolutionRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `perPage` | `int` |
| `count` | `int` |
| `solutions` | `list[Article]` |
| `problem` | `ProblemSketch` |
| `acceptSolution` | `bool` |

### `ProblemSetDataRequestResponse`

`ProblemSetDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `training` | `ProblemSetDetails` |
| `canEdit` | `bool` |
| `privilegedTeams` | `list[TeamSummary]` |

### `ContestDataRequestResponse`

`ContestDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `contest` | `ContestDetails` |
| `joined` | `bool` |
| `accessLevel` | `int` |

### `ContestListRequestResponse`

`ContestListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `contests` | `list[ContestSummary]` |
| `count` | `int` |
| `perPage` | `int` |

### `UserDataRequestResponse`

`UserDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `UserDetails` |
| `passedProblems` | `list[ProblemSummary]` |
| `submittedProblems` | `list[ProblemSummary]` |
| `teams` | `list[TeamSummary]` |

### `DiscussionRequestResponse`

`DiscussionRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `forum` | `Forum` |
| `post` | `Post` |
| `count` | `int` |
| `perPage` | `int` |
| `replies` | `list[Reply]` |
| `canReply` | `bool` |

### `ActivityRequestResponse`

`ActivityRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `activities` | `list[Activity]` |
| `count` | `int` |
| `perPage` | `int` |

### `TeamDataRequestResponse`

`TeamDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `team` | `TeamDetail` |
| `currentTeamMember` | `TeamMember` |
| `latestDiscussions` | `list[PostSummary]` |
| `groups` | `list[Group]` |
| `usages` | `dict[str, tuple[int, int]]` |

### `TeamMemberRequestResponse`

`TeamMemberRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `members` | `list[TeamMember]` |
| `perPage` | `int` |
| `count` | `int` |
| `group` | `Group` |

### `PasteRequestResponse`

`PasteRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `paste` | `Paste` |
| `canEdit` | `bool` |

### `ArticleDataRequestResponse`

`ArticleDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `article` | `Article` |
| `favored` | `bool` |
| `voted` | `int` |
| `canReply` | `bool` |
| `canEdit` | `bool` |

### `RecordRequestResponse`

`RecordRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `record` | `RecordDetails` |
| `showStatus` | `bool` |

### `TagRequestResponse`

`TagRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `tags` | `list[TagDetail]` |
| `types` | `list[TagType]` |

### `SubmitCodeResponse`

`SubmitCodeResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `rid` | `int` |

### `RawDataResponse`

`RawDataResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `data` | `Any` |

### `EmptyResponse`

`EmptyResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `ok` | `bool` |
| `_empty` | `bool` |

### `ArticleListRequestResponse`

`ArticleListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `articles` | `list[Article]` |
| `count` | `int` |
| `perPage` | `int` |

### `ArticleReplyListResponse`

`ArticleReplyListResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `replies` | `list[Reply]` |
| `count` | `int` |
| `perPage` | `int` |

### `Blog`

`Blog` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `title` | `str` |
| `content` | `str` |
| `identifier` | `str` |
| `type` | `str` |
| `status` | `int` |
| `top` | `int` |
| `time` | `int` |
| `author` | `UserSummary` |
| `replyCount` | `int` |
| `upvote` | `int` |

### `BlogListRequestResponse`

`BlogListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `blogs` | `list[Blog]` |
| `count` | `int` |
| `perPage` | `int` |

### `BlogDataRequestResponse`

`BlogDataRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `blog` | `Blog` |
| `canEdit` | `bool` |
| `canReply` | `bool` |
| `voted` | `int` |

### `BlogReplyListResponse`

`BlogReplyListResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `replies` | `list[Reply]` |
| `count` | `int` |
| `perPage` | `int` |

### `ChatMessage`

`ChatMessage` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `sender` | `UserSummary` |
| `receiver` | `UserSummary` |
| `content` | `str` |
| `time` | `int` |
| `read` | `bool` |

### `ChatRecordRequestResponse`

`ChatRecordRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `records` | `list[ChatMessage]` |
| `count` | `int` |
| `perPage` | `int` |

### `ImageListRequestResponse`

`ImageListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `images` | `list[Image]` |
| `count` | `int` |
| `perPage` | `int` |

### `UploadLink`

`UploadLink` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `host` | `str` |
| `policy` | `str` |
| `accessKeyID` | `str` |
| `callback` | `str` |
| `signature` | `str` |
| `expiredTime` | `int` |
| `dir` | `str` |

### `GenerateUploadLinkResponse`

`GenerateUploadLinkResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `uploadLink` | `UploadLink` |

### `RankingUser`

`RankingUser` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `uid` | `int` |
| `name` | `str` |
| `avatar` | `str` |
| `slogan` | `str` |
| `badge` | `str` |
| `isAdmin` | `bool` |
| `isBanned` | `bool` |
| `isRoot` | `bool` |
| `color` | `str` |
| `ccfLevel` | `int` |
| `xcpcLevel` | `int` |
| `background` | `str` |
| `ranking` | `int` |
| `rating` | `int` |
| `elo` | `EloRatingSummary` |

### `RankingListRequestResponse`

`RankingListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `users` | `list[RankingUser]` |
| `count` | `int` |
| `perPage` | `int` |

### `Notification`

`Notification` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `type` | `int` |
| `content` | `str` |
| `time` | `int` |
| `read` | `bool` |
| `sender` | `UserSummary` |

### `NotificationListRequestResponse`

`NotificationListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `notifications` | `list[Notification]` |
| `count` | `int` |
| `perPage` | `int` |

### `AdvertisementResponse`

`AdvertisementResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `data` | `Any` |

### `PaintboardTokenResponse`

`PaintboardTokenResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `token` | `str` |

### `PasteListRequestResponse`

`PasteListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `pastes` | `list[Paste]` |
| `count` | `int` |
| `perPage` | `int` |

### `RecordListRequestResponse`

`RecordListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `records` | `list[Record]` |
| `count` | `int` |
| `perPage` | `int` |

### `DownloadableTestcaseResponse`

`DownloadableTestcaseResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `testcases` | `list[str]` |
| `data` | `Any` |

### `TeamListRequestResponse`

`TeamListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `teams` | `list[TeamSummary]` |
| `count` | `int` |
| `perPage` | `int` |

### `Theme`

`Theme` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `id` | `int` |
| `name` | `str` |
| `user` | `UserSummary` |
| `header` | `dict[str, Any]` |
| `sideNav` | `dict[str, Any]` |
| `footer` | `dict[str, Any]` |
| `createTime` | `int` |
| `updateTime` | `int` |

### `ThemeListRequestResponse`

`ThemeListRequestResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `themes` | `list[Theme]` |
| `count` | `int` |
| `perPage` | `int` |

### `UserPracticeResponse`

`UserPracticeResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `problems` | `list[ProblemSummary]` |
| `count` | `int` |
| `perPage` | `int` |
| `data` | `Any` |

### `UserSettingResponse`

`UserSettingResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `UserDetails` |
| `settings` | `dict[str, Any]` |
| `data` | `Any` |

### `AuthResponse`

`AuthResponse` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `user` | `UserDetails` |
| `locked` | `bool` |
| `data` | `Any` |

### `LuoguCookies`

`LuoguCookies` 数据结构。

| 字段 | 类型/定义域 |
| --- | --- |
| `__client_id` | `str` |
| `_uid` | `str` |

### `ProblemType`

`ProblemType` 类型别名。

- 定义域：`Literal['P', 'U', 'T', 'B', 'CF', 'AT', 'UVA', 'SP']`

### `ProblemSetType`

`ProblemSetType` 类型别名。

- 定义域：`Literal['official', 'select']`

### `TransferProblemType`

`TransferProblemType` 类型别名。

- 定义域：`Literal['P', 'U', 'B'] | int`

### `JsonValue`

`JsonValue` 类型别名。

- 定义域：`str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]`

### `JsonObject`

`JsonObject` 类型别名。

- 定义域：`dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]`

### `JsonMapping`

`JsonMapping` 类型别名。

- 定义域：`Mapping[str, object]`

### `EditArticleRequest`

`EditArticleRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `title` | `str` | 否 |
| `category` | `int` | 否 |
| `content` | `str` | 否 |
| `solutionFor` | `str | None` | 否 |
| `status` | `int` | 否 |
| `top` | `int` | 否 |

### `BatchEditArticleRequest`

`BatchEditArticleRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `status` | `int` | 否 |
| `category` | `int` | 否 |
| `lids` | `list[str]` | 否 |

### `RegisterRequest`

`RegisterRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `username` | `str` | 否 |
| `password` | `str` | 否 |
| `endpoint` | `str` | 否 |
| `endpointType` | `int` | 否 |
| `verificationCode` | `str` | 否 |

### `OpenIdAuthRequest`

`OpenIdAuthRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `code` | `str` | 否 |
| `state` | `str` | 否 |
| `redirectURI` | `str` | 否 |

### `AuthUnlockRequest`

`AuthUnlockRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `password` | `str` | 否 |
| `captcha` | `str` | 否 |
| `code` | `str` | 否 |

### `EditBlogRequest`

`EditBlogRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `title` | `str` | 否 |
| `content` | `str` | 否 |
| `identifier` | `str` | 否 |
| `type` | `str` | 否 |
| `top` | `int` | 否 |
| `status` | `int` | 否 |
| `csrf_token` | `str` | 否 |

### `BlogAdminForm`

`BlogAdminForm` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `method` | `str` | 否 |
| `ids` | `list[int]` | 否 |
| `status` | `int` | 否 |
| `type` | `str` | 否 |

### `ContestJoinRequest`

`ContestJoinRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `code` | `str` | 否 |
| `invitationCode` | `str` | 否 |
| `password` | `str` | 否 |

### `EditContestRequest`

`EditContestRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `settings` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |
| `hostID` | `int | None` | 否 |

### `EditContestProblemRequest`

`EditContestProblemRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `problems` | `list[str]` | 否 |
| `pids` | `list[str]` | 否 |

### `CreatePostRequest`

`CreatePostRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `captcha` | `str` | 否 |
| `content` | `str` | 否 |
| `title` | `str` | 否 |
| `forum` | `str` | 否 |

### `GenerateUploadLinkRequest`

`GenerateUploadLinkRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `filename` | `str` | 否 |
| `fileName` | `str` | 否 |
| `size` | `int` | 否 |
| `type` | `str` | 否 |
| `mimeType` | `str` | 否 |

### `EditPasteRequest`

`EditPasteRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `data` | `str` | 否 |
| `public` | `bool` | 否 |

### `EditTrainingRequest`

`EditTrainingRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `title` | `str` | 否 |
| `name` | `str` | 否 |
| `description` | `str` | 否 |
| `type` | `int` | 否 |
| `providerID` | `int | None` | 否 |

### `EditTrainingProblemsRequest`

`EditTrainingProblemsRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `problems` | `list[str]` | 否 |
| `pids` | `list[str]` | 否 |

### `TranslateProblemRequest`

`TranslateProblemRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `locale` | `str` | 否 |
| `content` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |

### `TeamJoinRequest`

`TeamJoinRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `reason` | `str` | 否 |
| `message` | `str` | 否 |

### `EditTeamRequest`

`EditTeamRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `name` | `str` | 否 |
| `description` | `str` | 否 |
| `notice` | `str` | 否 |
| `contact` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |
| `joinPermission` | `int` | 否 |

### `TeamMemberUpdateRequest`

`TeamMemberUpdateRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `realName` | `str` | 否 |
| `group` | `str` | 否 |
| `permission` | `int` | 否 |

### `EditThemeRequest`

`EditThemeRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `name` | `str` | 否 |
| `header` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |
| `sideNav` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |
| `footer` | `dict[str, str | int | float | bool | None | list[str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]] | dict[str, str | int | float | bool | None | list[ForwardRef('JsonValue')] | dict[str, ForwardRef('JsonValue')]]]` | 否 |

### `UserPreferenceUpdateRequest`

`UserPreferenceUpdateRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `background` | `str` | 否 |
| `color` | `str` | 否 |
| `theme` | `int` | 否 |
| `language` | `str` | 否 |

### `BindRemoteJudgeAccountRequest`

`BindRemoteJudgeAccountRequest` 请求体结构。

| 字段 | 类型/定义域 | 必填 |
| --- | --- | --- |
| `oj` | `str` | 否 |
| `username` | `str` | 否 |
| `password` | `str` | 否 |
| `captcha` | `str` | 否 |
