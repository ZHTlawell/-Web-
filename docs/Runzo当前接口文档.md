# Runzo 当前实现接口文档

## 1. 文档说明

本文档基于当前仓库里的实际接口代码整理，对应实现文件主要是：

- [api_routes.py](/Users/macmini/Desktop/测试平台/app/routes/api_routes.py)
- [validation_service.py](/Users/macmini/Desktop/测试平台/app/services/validation_service.py)
- [runzo.py](/Users/macmini/Desktop/测试平台/app/models/runzo.py)

这是一份“当前代码真实行为”文档，不是未来规划稿。

## 2. 当前接口特征

### 2.1 接口前缀

当前接口统一前缀为：

```text
/api/runzo
```

### 2.2 请求体格式

当前 `POST` 接口都按表单方式取参：

- `application/x-www-form-urlencoded`
- 或 `multipart/form-data`

当前代码**不是**按 `application/json` 取参。

### 2.3 响应模式

当前接口有两种响应模式：

1. 普通接口模式  
不传 `HX-Request: true` 时，返回 JSON。

2. HTMX 页面模式  
传 `HX-Request: true` 时，返回 HTML 片段，供当前 Web 页面局部刷新。

如果是 iOS / App / 原生前端对接，建议**不要传** `HX-Request: true`，只用 JSON 模式。

### 2.4 会话机制

多数据上传相关接口依赖浏览器 Cookie 会话：

- Cookie 名：`runzo_session_id`

当前逻辑不是 `taskId` 路由模式，而是“同一个浏览器会话对应一个任务上下文”。

这意味着：

- `start`
- `continue`
- `cancel`
- `status`

这 4 个接口必须在同一个会话上下文下调用，才能操作同一个任务。

### 2.5 关于 `ts-app-version`

当前代码里，`ts-app-version` 支持两种传法：

1. 请求头：
   - `ts-app-version`
   - 或 `x-ts-app-version`
2. 表单字段：
   - `tsAppVersion`

优先级：

- 请求头优先
- 如果请求头没有，再读表单字段

## 3. 通用约定

### 3.1 当前实际使用到的请求头

| 字段名 | 必填 | 用途 | 说明 |
| --- | --- | --- | --- |
| `HX-Request` | 否 | 切换 HTML 片段响应 | 传 `true` 时返回 HTML，不传时返回 JSON |
| `ts-app-version` | 否 | 设置下游 `watch-settle` 请求头 | 优先级高于表单字段 `tsAppVersion` |
| `x-ts-app-version` | 否 | 同上 | 兼容写法 |

补充说明：

- 当前代码**不会**从请求头中读取 `Authorization`
- 当前代码**不会**从请求头中读取 `ts-user-id`
- `Authorization`、`userId` 仍然是表单字段

### 3.2 通用错误规则

当前接口常见错误返回：

- HTTP 状态码：`400`
- 返回体：JSON 或 HTML 片段，取决于是否传了 `HX-Request: true`

常见失败原因：

- 必填字段为空
- 参数格式不合法
- 当前任务状态不允许继续/终止
- `simulate` 或 `watch-settle` 调用失败

## 4. 多数据上传接口

## 4.1 启动任务

- 方法：`POST`
- 路径：`/api/runzo/start`
- 作用：创建并启动当前会话下的多数据上传任务

### 请求字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `environment` | string | 否 | 运行环境，默认 `test`，可选 `test` / `preprod` |
| `userId` | string | 是 | 用户 ID |
| `authorization` | string | 是 | Bearer Token |
| `tsAppVersion` | string | 条件必填 | 当请求头没有 `ts-app-version` / `x-ts-app-version` 时必填 |
| `startFromDayStartTime` | integer | 否 | 断点起跑时间，留空表示 `None` |
| `mongoCreateBy` | string | 否 | Mongo 查询 `createBy`，留空时默认取 `userId` |
| `gender` | string | 否 | 默认 `male` |
| `age` | integer | 否 | 默认 `22`，必须大于 0 |
| `weight` | number | 否 | 默认 `75`，必须大于 0 |
| `height` | number | 否 | 默认 `175`，必须大于 0 |
| `hrMax` | integer | 否 | 默认 `198`，必须大于 0 |
| `hrRest` | integer | 否 | 默认 `65`，必须大于 0 |
| `targetDistance` | number | 否 | 默认 `5`，必须大于 0 |
| `intensityPreference` | string | 否 | 默认 `medium` |

### 请求示例

```bash
curl -X POST 'http://host/api/runzo/start' \
  -H 'ts-app-version: 2.6.0' \
  -d 'environment=preprod' \
  -d 'userId=92114529545000186' \
  -d 'authorization=Bearer xxx' \
  -d 'startFromDayStartTime=1773676800000' \
  -d 'mongoCreateBy=85123806571000115' \
  -d 'gender=male' \
  -d 'age=22' \
  -d 'weight=75' \
  -d 'height=175' \
  -d 'hrMax=198' \
  -d 'hrRest=65' \
  -d 'targetDistance=5' \
  -d 'intensityPreference=medium'
```

### 成功响应

```json
{
  "success": true,
  "message": "任务已启动。",
  "data": {
    "task_id": "7f4caa4d-70c8-4dc8-a8cb-c01f6d5164c4",
    "status": "执行中",
    "summary": "任务已创建，等待开始读取训练计划。",
    "environment": "test",
    "checkpoint_type": null,
    "checkpoint_message": null,
    "current_week": null,
    "current_training_type": null,
    "current_day_start_time": null,
    "completed_count": 0,
    "logs": [
      {
        "timestamp": "2026-03-16T18:30:00.000000",
        "level": "信息",
        "message": "任务已创建，准备开始执行。"
      }
    ],
    "error_message": null,
    "masked_token": "Bearer xxx...123456"
  }
}
```

### 失败响应

```json
{
  "success": false,
  "message": "启动失败：该字段不能为空",
  "data": {
    "task_id": null,
    "status": "待开始",
    "summary": "尚未开始执行任务。",
    "environment": "test",
    "checkpoint_type": null,
    "checkpoint_message": null,
    "current_week": null,
    "current_training_type": null,
    "current_day_start_time": null,
    "completed_count": 0,
    "logs": [],
    "error_message": null,
    "masked_token": null
  }
}
```

## 4.2 查询当前任务状态

- 方法：`GET`
- 路径：`/api/runzo/status`
- 作用：查询当前会话下的任务状态

### 请求参数

无。

### 成功响应

```json
{
  "success": true,
  "message": "获取成功。",
  "data": {
    "task_id": "7f4caa4d-70c8-4dc8-a8cb-c01f6d5164c4",
    "status": "等待确认",
    "summary": "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。",
    "environment": "preprod",
    "checkpoint_type": "首次类型确认",
    "checkpoint_message": "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。",
    "current_week": 2,
    "current_training_type": "Interval",
    "current_day_start_time": 1774108800000,
    "completed_count": 3,
    "logs": [
      {
        "timestamp": "2026-03-16T18:30:00.000000",
        "level": "警告",
        "message": "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。"
      }
    ],
    "error_message": null,
    "masked_token": "Bearer xxx...123456"
  }
}
```

### 字段说明

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string \| null | 当前任务 ID |
| `status` | string | 当前任务状态，枚举值见下方 |
| `summary` | string | 当前任务摘要 |
| `environment` | string | `test` 或 `preprod` |
| `checkpoint_type` | string \| null | 当前检查点类型 |
| `checkpoint_message` | string \| null | 当前检查点提示语 |
| `current_week` | integer \| null | 当前周 |
| `current_training_type` | string \| null | 当前训练类型 |
| `current_day_start_time` | integer \| null | 当前训练 dayStartTime |
| `completed_count` | integer | 已完成数量 |
| `logs` | array | 日志列表，最新日志在最前面 |
| `error_message` | string \| null | 失败信息 |
| `masked_token` | string \| null | 脱敏后的 Authorization |

### `status` 枚举值

| 值 | 说明 |
| --- | --- |
| `待开始` | 当前会话还没有启动任务 |
| `执行中` | 后台线程正在执行 |
| `等待确认` | 到达检查点，等待继续 |
| `已完成` | 全部任务执行完成 |
| `已失败` | 执行失败 |
| `已终止` | 用户主动终止 |

### `checkpoint_type` 枚举值

| 值 | 说明 |
| --- | --- |
| `首次类型确认` | 已完成 Easy/LSD、Threshold、Interval 各一次 |
| `周切换确认` | 当前周执行完成，等待继续下一周 |

### `logs[].level` 枚举值

| 值 | 说明 |
| --- | --- |
| `信息` | 普通信息 |
| `成功` | 成功日志 |
| `警告` | 检查点或提示 |
| `错误` | 错误日志 |

## 4.3 继续执行任务

- 方法：`POST`
- 路径：`/api/runzo/continue`
- 作用：继续执行当前会话下处于“等待确认”的任务

### 请求参数

无。

### 成功响应

```json
{
  "success": true,
  "message": "任务已继续执行。",
  "data": {
    "task_id": "7f4caa4d-70c8-4dc8-a8cb-c01f6d5164c4",
    "status": "执行中",
    "summary": "已收到继续指令，任务恢复执行。",
    "environment": "preprod",
    "checkpoint_type": null,
    "checkpoint_message": null,
    "current_week": 2,
    "current_training_type": "Interval",
    "current_day_start_time": 1774108800000,
    "completed_count": 3,
    "logs": [],
    "error_message": null,
    "masked_token": "Bearer xxx...123456"
  }
}
```

### 失败场景

- 当前没有任务
- 当前任务不是“等待确认”状态

失败时返回 `400`。

## 4.4 终止任务

- 方法：`POST`
- 路径：`/api/runzo/cancel`
- 作用：终止当前会话下的任务

### 请求参数

无。

### 成功响应

```json
{
  "success": true,
  "message": "任务已终止。",
  "data": {
    "task_id": "7f4caa4d-70c8-4dc8-a8cb-c01f6d5164c4",
    "status": "已终止",
    "summary": "任务已被人工终止。",
    "environment": "test",
    "checkpoint_type": null,
    "checkpoint_message": null,
    "current_week": 1,
    "current_training_type": "Easy",
    "current_day_start_time": 1773676800000,
    "completed_count": 1,
    "logs": [],
    "error_message": null,
    "masked_token": "Bearer xxx...123456"
  }
}
```

## 5. 单数据上传接口

## 5.1 执行单数据上传

- 方法：`POST`
- 路径：`/api/runzo/single-upload/execute`
- 作用：完成一条训练的 `simulate -> watch-settle` 同步调用

### 请求字段

#### 公共字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `environment` | string | 否 | 运行环境，默认 `test` |
| `userId` | string | 是 | 用户 ID |
| `authorization` | string | 是 | Bearer Token |
| `tsAppVersion` | string | 条件必填 | 当请求头没有 `ts-app-version` / `x-ts-app-version` 时必填 |
| `dailyId` | string | 是 | 日计划 ID |
| `trainingType` | string | 是 | 训练类型 |
| `runningDistance` | number | 是 | 跑量距离，必须大于 0 |
| `stateDescription` | string | 否 | 自然语言描述调整训练数据强度 |
| `weekIndex` | integer | 否 | 周序号，必须大于 0 |
| `dayStartTime` | integer | 否 | 起始时间，必须大于 0 |
| `gender` | string | 否 | 默认 `male` |
| `age` | integer | 否 | 默认 `22` |
| `weight` | number | 否 | 默认 `75` |
| `height` | number | 否 | 默认 `175` |
| `hrMax` | integer | 否 | 默认 `198` |
| `hrRest` | integer | 否 | 默认 `65` |
| `targetDistance` | number | 否 | 默认 `5` |
| `intensityPreference` | string | 否 | 默认 `medium` |

#### `Easy` / `LSD` / `Rest` / `ExtraSession` 额外字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `easyMinPace` | string | 是 | 主训练最小配速 |
| `easyMaxPace` | string | 是 | 主训练最大配速 |

#### `Threshold` 额外字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `thresholdWarmupMinPace` | string | 是 | 热身最小配速 |
| `thresholdWarmupMaxPace` | string | 是 | 热身最大配速 |
| `thresholdWarmupDistance` | number | 否 | 热身距离 |
| `thresholdMainMinPace` | string | 是 | 主段最小配速 |
| `thresholdMainMaxPace` | string | 是 | 主段最大配速 |
| `thresholdMainDistance` | number | 否 | 主段距离 |

#### `Interval` 额外字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `intervalBlock1MinPace` | string | 是 | 热身段最小配速 |
| `intervalBlock1MaxPace` | string | 是 | 热身段最大配速 |
| `intervalBlock1Distance` | number | 是 | 热身段距离 |
| `intervalBlock2MinPace` | string | 是 | 主训练段最小配速 |
| `intervalBlock2MaxPace` | string | 是 | 主训练段最大配速 |
| `intervalBlock2Distance` | number | 是 | 主训练段距离 |
| `intervalRepeatNum` | integer | 否 | 循环次数，默认 `1` |
| `intervalBlock3MinPace` | string | 是 | 慢跑段最小配速 |
| `intervalBlock3MaxPace` | string | 是 | 慢跑段最大配速 |
| `intervalBlock3Distance` | number | 是 | 慢跑段距离 |

### 单数据上传真实返回结构

当前 JSON 响应没有统一包一层 `data`，而是直接返回结果对象。

### 成功响应

```json
{
  "success": true,
  "environment": "test",
  "execution_status": "执行成功",
  "summary": "单数据上传执行成功。",
  "error_message": null,
  "simulate_request": "{...JSON字符串...}",
  "simulate_response": "{...JSON字符串...}",
  "settlement_request": "{...JSON字符串...}",
  "settlement_response": "{...JSON字符串...}"
}
```

### 失败响应

```json
{
  "success": false,
  "environment": "test",
  "execution_status": "执行失败",
  "summary": "单数据上传执行失败。",
  "error_message": "主训练最小配速不能为空",
  "simulate_request": "",
  "simulate_response": "",
  "settlement_request": "",
  "settlement_response": ""
}
```

### 返回字段说明

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `success` | boolean | 是否执行成功 |
| `environment` | string | `test` 或 `preprod` |
| `execution_status` | string | 当前执行状态，默认 `待开始`，执行中为 `执行中`，成功为 `执行成功`，失败为 `执行失败` |
| `summary` | string | 简要描述 |
| `error_message` | string \| null | 错误信息 |
| `simulate_request` | string | simulate 请求体，JSON 字符串 |
| `simulate_response` | string | simulate 响应体，JSON 字符串 |
| `settlement_request` | string | settlement 请求体，JSON 字符串 |
| `settlement_response` | string | settlement 响应体，JSON 字符串 |

## 6. 当前接口与前端原生对接的注意点

### 6.1 如果前端不是网页，而是 App / iOS / 原生端

当前实现可对接，但要注意：

- 多数据上传依赖 Cookie 会话
- 不是显式 `taskId` 接口风格
- 当前 `POST` 请求是表单参数，不是 JSON
- 单数据上传返回的是扁平结果对象，不是统一包裹结构

也就是说：

- 当前版本可以用于联调
- 但如果后续要给 iOS 原生长期使用，建议再做一版纯接口化改造

### 6.2 当前最适合的调用方式

#### 多数据上传

- 同一个客户端容器中保持 Cookie
- 依次调用：
  1. `/api/runzo/start`
  2. `/api/runzo/status`
  3. `/api/runzo/continue`
  4. `/api/runzo/cancel`

#### 单数据上传

- 直接调用 `/api/runzo/single-upload/execute`
- 普通 JSON 响应即可

## 7. 建议

如果你接下来要给 iOS / 前端正式对接，我建议把下一版接口再收敛成：

- JSON 请求体
- 显式 `taskId`
- 不依赖 Cookie
- 单数据上传和多数据上传统一响应结构

但这份文档描述的是**当前代码已经实现好的接口行为**，前端如果现在就要联调，应以本文档为准。
