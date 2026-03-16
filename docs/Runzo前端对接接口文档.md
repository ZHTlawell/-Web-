# Runzo 前端对接接口文档

## 1. 文档说明

本文档用于 Runzo 业务与 iOS / App / H5 前端对接时的接口约定说明。

本文档定义的是平台层接口，不要求前端直接对接下游 `simulate` 或 `watch-settle` 接口。

后端负责：

- 参数校验
- 环境切换
- Mongo 读取
- `simulate` 调用
- `watch-settle` 调用
- 业务状态判断
- 任务状态推进

前端负责：

- 参数录入
- 请求头传递
- 按接口返回展示页面
- 根据接口状态控制“开始执行 / 继续执行 / 终止任务”等按钮

## 2. 通用约定

### 2.1 接口前缀

建议统一前缀：

```text
/api/v1/runzo
```

说明：

- 本文档为前端对接设计稿，路径按后续对外接口规范整理
- 当前项目页面版接口可逐步收敛到本文档定义

### 2.2 请求格式

- 请求方法：`GET` / `POST`
- 请求体格式：`application/json`
- 字符编码：`UTF-8`

### 2.3 通用请求头

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `Authorization` | string | 是 | 用户令牌，例如 `Bearer xxx` |
| `ts-user-id` | string | 是 | 当前用户 ID |
| `ts-app-version` | string | 是 | App 当前版本号，例如 `2.6.0` |
| `x-runzo-env` | string | 是 | 运行环境，枚举：`test` / `preprod` |
| `lang` | string | 否 | 语言，默认 `zh_CN` |
| `ts-time-zone-id` | string | 否 | 时区，默认 `Asia/Shanghai` |
| `ts-country` | string | 否 | 国家码，默认 `CN` |
| `x-runzo-debug` | string | 否 | 调试开关，传 `true` 时可返回调试字段 |

补充说明：

- 前端传入的 `ts-app-version` 会透传到下游 `watch-settle` 请求头
- 前端不需要关心下游 `simulate` / `watch-settle` 的请求头细节

### 2.4 通用响应结构

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败响应：

```json
{
  "code": 4001,
  "message": "参数错误：dailyId 不能为空",
  "data": null
}
```

### 2.5 通用响应码

| code | 说明 |
| --- | --- |
| `0` | 成功 |
| `4001` | 参数错误 |
| `4002` | 当前状态不允许该操作 |
| `4003` | `simulate` 调用失败 |
| `4004` | `watch-settle` 调用失败 |
| `5000` | 服务内部异常 |

### 2.6 通用枚举

#### 运行环境 `x-runzo-env`

| 枚举值 | 说明 |
| --- | --- |
| `test` | 测试环境 |
| `preprod` | 预发布环境 |

#### 训练类型 `trainingType`

| 枚举值 | 说明 |
| --- | --- |
| `Easy` | 轻松跑 |
| `LSD` | 长距离慢跑 |
| `Rest` | 休息训练 |
| `ExtraSession` | 额外训练 |
| `Threshold` | 阈值训练 |
| `Interval` | 间歇训练 |

#### 多任务状态 `status`

| 枚举值 | 说明 |
| --- | --- |
| `pending` | 待开始 |
| `running` | 执行中 |
| `waiting_confirm` | 等待继续 |
| `success` | 已完成 |
| `failed` | 已失败 |
| `cancelled` | 已终止 |

#### 检查点类型 `checkpointType`

| 枚举值 | 说明 |
| --- | --- |
| `none` | 无检查点 |
| `first_round_completed` | 已完成 Easy/LSD、Threshold、Interval 各一次 |
| `week_completed` | 当前周训练完成，等待下一周继续 |

#### 日志级别 `level`

| 枚举值 | 说明 |
| --- | --- |
| `info` | 信息 |
| `success` | 成功 |
| `warning` | 警告 |
| `error` | 错误 |

## 3. 单数据上传接口

### 3.1 接口说明

- 接口名称：单数据上传执行
- 接口用途：前端传入单条训练数据参数，后端完成 `simulate -> watch-settle` 的一次完整调用
- 接口类型：同步接口

### 3.2 请求信息

- 方法：`POST`
- 路径：`/api/v1/runzo/single-upload/execute`

### 3.3 请求体字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `dailyId` | string | 是 | 训练计划唯一标识 |
| `trainingType` | string | 是 | 训练类型，见上方枚举 |
| `runningDistance` | number | 是 | 目标距离，必须大于 0 |
| `trainingBlocks` | array<object> | 是 | 训练块数组，结构随训练类型变化 |
| `stateDescription` | string | 否 | 自然语言描述，用于调整训练数据强度 |
| `weekIndex` | integer | 否 | 周序号 |
| `dayStartTime` | integer | 否 | 当天开始时间，毫秒时间戳 |
| `userData` | object | 是 | 用户画像对象 |

### 3.4 userData 字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `gender` | string | 是 | 性别 |
| `age` | integer | 是 | 年龄，必须大于 0 |
| `weight` | number | 是 | 体重，必须大于 0 |
| `height` | number | 是 | 身高，必须大于 0 |
| `hrMax` | integer | 是 | 最大心率，必须大于 0 |
| `hrRest` | integer | 是 | 静息心率，必须大于 0 |
| `targetDistance` | number | 是 | 用户目标距离，必须大于 0 |
| `intensityPreference` | string | 是 | 强度偏好，例如 `low` / `medium` / `high` |

### 3.5 trainingBlocks 结构说明

前端按 `trainingType` 组织 `trainingBlocks`。

#### 1. `Easy` / `LSD` / `Rest` / `ExtraSession`

`trainingBlocks` 固定为 1 个对象：

```json
[
  {
    "minPace": "6:00",
    "maxPace": "6:30"
  }
]
```

#### 2. `Threshold`

`trainingBlocks` 固定为 2 个对象，依次表示热身段和主训练段：

```json
[
  {
    "minPace": "6:00",
    "maxPace": "6:30",
    "distance": 2
  },
  {
    "minPace": "4:30",
    "maxPace": "4:45",
    "distance": 4
  }
]
```

#### 3. `Interval`

`trainingBlocks` 固定为 2 个对象：

- 第 1 个对象：热身段
- 第 2 个对象：循环段

```json
[
  {
    "distance": 0.5,
    "minPace": "7:20",
    "maxPace": "7:50"
  },
  {
    "repeatNum": 3,
    "intervalDistance": 0.8,
    "intervalMinPace": "5:10",
    "intervalMaxPace": "5:40",
    "joggingDistance": 0.2,
    "joggingMinPace": "7:20",
    "joggingMaxPace": "7:50"
  }
]
```

### 3.6 请求示例

```json
{
  "dailyId": "daily-001",
  "trainingType": "Interval",
  "runningDistance": 4.5,
  "stateDescription": "今天有点累",
  "weekIndex": 2,
  "dayStartTime": 1774108800000,
  "userData": {
    "gender": "male",
    "age": 22,
    "weight": 75,
    "height": 175,
    "hrMax": 198,
    "hrRest": 65,
    "targetDistance": 5,
    "intensityPreference": "medium"
  },
  "trainingBlocks": [
    {
      "distance": 0.5,
      "minPace": "7:20",
      "maxPace": "7:50"
    },
    {
      "repeatNum": 3,
      "intervalDistance": 0.8,
      "intervalMinPace": "5:10",
      "intervalMaxPace": "5:40",
      "joggingDistance": 0.2,
      "joggingMinPace": "7:20",
      "joggingMaxPace": "7:50"
    }
  ]
}
```

### 3.7 标准返回字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 是 | 执行状态，枚举：`success` / `failed` |
| `summary` | string | 是 | 当前执行摘要 |
| `environment` | string | 是 | 当前运行环境 |
| `dailyId` | string | 是 | 当前执行的 `dailyId` |
| `trainingType` | string | 是 | 当前执行的训练类型 |
| `errorMessage` | string | 否 | 失败时返回错误信息 |

### 3.8 调试模式返回字段

仅在请求头传入 `x-runzo-debug: true` 时建议返回：

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `debugData.simulateRequest` | object | 否 | simulate 请求体 |
| `debugData.simulateResponse` | object | 否 | simulate 响应体 |
| `debugData.settlementRequest` | object | 否 | watch-settle 请求体 |
| `debugData.settlementResponse` | object | 否 | watch-settle 响应体 |

说明：

- 正式前端页面不建议依赖这些调试字段
- 该部分仅用于内部联调、排查问题或测试平台页面展示

### 3.9 成功响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "success",
    "summary": "单数据上传执行成功",
    "environment": "preprod",
    "dailyId": "daily-001",
    "trainingType": "Interval"
  }
}
```

### 3.10 失败响应示例

```json
{
  "code": 4004,
  "message": "watch-settle 调用失败",
  "data": {
    "status": "failed",
    "summary": "单数据上传执行失败",
    "environment": "preprod",
    "dailyId": "daily-001",
    "trainingType": "Interval",
    "errorMessage": "settlement 接口失败（500）：xxx"
  }
}
```

## 4. 多数据上传任务接口

### 4.1 接口说明

- 接口名称：多数据上传任务接口
- 接口用途：根据 `createBy` 从 Mongo 读取训练计划，按顺序执行 `simulate -> watch-settle`
- 接口类型：异步任务接口

说明：

- 任务启动后，前端通过 `taskId` 查询状态
- `taskId` 由后端随机生成，建议使用 UUID
- 每次启动新任务，都会生成新的 `taskId`

### 4.2 启动任务

#### 请求信息

- 方法：`POST`
- 路径：`/api/v1/runzo/tasks/start`

#### 请求体字段

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `mongoCreateBy` | string | 否 | Mongo 查询条件，缺省时取请求头 `ts-user-id` |
| `startFromDayStartTime` | integer | 否 | 断点起跑时间，毫秒时间戳 |
| `userData` | object | 是 | 用户画像对象，结构同单数据上传 |

#### 请求示例

```json
{
  "mongoCreateBy": "85123806571000115",
  "startFromDayStartTime": 1773676800000,
  "userData": {
    "gender": "male",
    "age": 22,
    "weight": 75,
    "height": 175,
    "hrMax": 198,
    "hrRest": 65,
    "targetDistance": 5,
    "intensityPreference": "medium"
  }
}
```

#### 返回字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID，后端随机生成 |
| `status` | string | 是 | 当前任务状态 |
| `summary` | string | 是 | 当前任务摘要 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "b7d5d2a5-6f08-4d61-a555-7d5e5f4d9f3e",
    "status": "running",
    "summary": "任务已创建，开始执行"
  }
}
```

### 4.3 查询任务状态

#### 请求信息

- 方法：`GET`
- 路径：`/api/v1/runzo/tasks/{taskId}`

#### 路径参数

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 启动任务后返回的任务 ID |

#### 返回字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID |
| `status` | string | 是 | 任务状态 |
| `checkpointType` | string | 是 | 检查点类型，无检查点时返回 `none` |
| `canContinue` | boolean | 是 | 是否允许继续执行 |
| `canCancel` | boolean | 是 | 是否允许终止 |
| `summary` | string | 是 | 当前任务摘要 |
| `currentWeek` | integer | 否 | 当前周序号 |
| `currentTrainingType` | string | 否 | 当前训练类型 |
| `currentDayStartTime` | integer | 否 | 当前训练 `dayStartTime` |
| `completedCount` | integer | 是 | 已完成数量 |
| `errorMessage` | string | 否 | 失败时返回错误信息 |
| `logs` | array<object> | 是 | 执行日志列表，最新日志排在最前面 |

#### logs 字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `time` | string | 是 | 日志时间 |
| `level` | string | 是 | 日志级别 |
| `message` | string | 是 | 日志内容 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "b7d5d2a5-6f08-4d61-a555-7d5e5f4d9f3e",
    "status": "waiting_confirm",
    "checkpointType": "first_round_completed",
    "canContinue": true,
    "canCancel": true,
    "summary": "已完成 Easy/LSD、Threshold、Interval 各一次，等待继续",
    "currentWeek": 2,
    "currentTrainingType": "Interval",
    "currentDayStartTime": 1774108800000,
    "completedCount": 6,
    "logs": [
      {
        "time": "2026-03-16 10:00:00",
        "level": "warning",
        "message": "已完成 Easy/LSD、Threshold、Interval 各一次，请点击继续执行。"
      }
    ]
  }
}
```

### 4.4 继续任务

#### 请求信息

- 方法：`POST`
- 路径：`/api/v1/runzo/tasks/{taskId}/continue`

#### 路径参数

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID |

#### 返回字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID |
| `status` | string | 是 | 当前任务状态 |
| `summary` | string | 是 | 当前任务摘要 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "b7d5d2a5-6f08-4d61-a555-7d5e5f4d9f3e",
    "status": "running",
    "summary": "任务继续执行"
  }
}
```

### 4.5 终止任务

#### 请求信息

- 方法：`POST`
- 路径：`/api/v1/runzo/tasks/{taskId}/cancel`

#### 路径参数

| 字段名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID |

#### 返回字段

| 字段名 | 类型 | 必返 | 说明 |
| --- | --- | --- | --- |
| `taskId` | string | 是 | 任务 ID |
| `status` | string | 是 | 当前任务状态 |
| `summary` | string | 是 | 当前任务摘要 |

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "taskId": "b7d5d2a5-6f08-4d61-a555-7d5e5f4d9f3e",
    "status": "cancelled",
    "summary": "任务已终止"
  }
}
```

## 5. 对接说明

### 5.1 前端必须做的事

- 正确传递通用请求头
- 单数据上传时按 `trainingType` 组织 `trainingBlocks`
- 多数据上传时保存 `taskId`
- 轮询任务状态接口
- 根据 `status`、`canContinue`、`canCancel` 控制页面按钮

### 5.2 后端必须做的事

- 对请求头和请求体做校验
- 调用下游 `simulate` 与 `watch-settle`
- 判断检查点
- 维护任务状态与日志
- 返回可供前端直接渲染的状态字段

### 5.3 不建议前端依赖的内容

- 下游 `simulate` 的原始协议细节
- 下游 `watch-settle` 的原始请求头
- 调试模式下的 `simulateRequest` / `simulateResponse` / `settlementRequest` / `settlementResponse`

### 5.4 可选扩展项

如后续需要排查问题，可在响应体中增加以下可选字段：

- `requestId`
- `debugData`

说明：

- `requestId` 不作为本期业务必返字段
- `taskId` 为多数据任务必返字段
