# Ai-Link A.O. Smith 热水器集成

用于 AI 家智控燃气热水器的 Home Assistant 自定义集成。通过史密斯云端控制设备，支持 HomeKit Bridge。

## v1.1.0 功能

| 功能 | Home Assistant | Apple 家庭（通过 HomeKit Bridge） |
|---|---|---|
| 设定水温、电源 | 热水器实体 + 温控实体 | 恒温器界面，选择 `climate` 实体 |
| 实际出水温度、加热状态 | 温控及传感器 | 恒温器当前温度与加热/待机状态 |
| 零冷水、节能半管零冷水 | 独立开关 | 独立开关 |
| 增压开关、1/2/3 档 | 三档增压实体 + 开关 | 风扇样式控件，33/67/100% 对应三档 |
| 零冷水时长 | 1–99 分钟整数输入 | 1/5/10/15/30/60/99 分钟快捷开关 |
| 风机转速、出水流量 | rpm、L/min 传感器 | Apple 家庭无原生数值显示类型 |

增压控件控制水泵增压，不控制燃烧风机。时长快捷开关只修改设备时长，不启动循环；当前选中时长显示为开启，点击关闭不清空时长。自定义分钟数在 Home Assistant 设置；不属于预设时所有预设开关关闭。

### 范围与状态来源

根据官方 GasWater 控制页面及 JSQ31-VJS 抓包核对：

- `waterTemp` 是**设定温度**；`outWaterTemp` 是**实际出水温度**。
- 支持最低 35°C 的设备范围为 35–70°C；`minTemp35=0` 时最低 37°C。
- 普通设备步进 1°C；HomeKit 传入的小数温度就近对齐设备步进并回显实际设定值。支持半度的设备在 50°C 以下步进 0.5°C，50°C 及以上为整数。
- 按官方 App 逻辑，在使用热水时禁止继续调高到 50°C 以上。
- 零冷水时长 1–99 分钟，不是累计运行时间。设备自身负责零冷水运行逻辑。
- 增压仅 1、2、3 档。
- 待机时可能有设定温度但未燃烧，界面根据 `heating` 回报显示实际加热状态。

### 本次修复

- 修正电源命令为 `SetDeviceOnOff`。
- 修正零冷水时长命令为 `WaterCruiseTimer`，参数名同名。
- 增压开关使用 `PressurizeOnOff` / `pressurize`，档位使用 `SetPressurizeLevel` / `pressurizeLevel`。
- 详细设备状态优先于可能过时的首页快照，避免控制后读回旧状态。
- HTTP/业务错误不再当作成功；命令串行执行，并等待设备状态回报确认。未确认会向调用方报错。
- 未知、离线状态不再伪装成默认温度或关闭。
- 出水温度传感器增加 HomeKit 所需的温度设备类别。

## 安装与更新

在 HACS 自定义仓库中添加 `https://github.com/mopocv/Ai-Link_A.O.Smith`，类别选 Integration，安装后重启 Home Assistant。也可以将 `custom_components/ailink_aosmith` 复制到 HA 的 `custom_components` 目录后重启。

在“设置 → 设备与服务 → 添加集成”搜索 Ai-Link A.O. Smith，填写从 AI 家智控抓包获取的 `access_token`、`user_id`、`family_id`，可选 Cookie 与手机号。令牌可带或不带 `Bearer ` 前缀。令牌过期后需更新认证信息。

默认每 60 秒轮询，可在集成选项中调整。控制操作会另外主动查询状态确认。

## HomeKit 配置

在 HomeKit Bridge 中选择：热水器**温控**、零冷水、节能半管、三档增压、实际出水温度，以及需要的时长预设。温控与原有 `water_heater` 只选一个，避免重复配件；三档增压包含开关，也可另外保留增压开关。

HomeKit 本身没有普通 `number` 实体；这里提供具有真实分钟名称的快捷开关。高级用法可以把零冷水 switch 配置为 `valve`，用单位为秒的 `input_number` 通过 `linked_valve_duration` 关联时长，并配置自动化与原始分钟实体双向同步；不同 HomeKit 客户端对阀门时长的编辑支持不同，不能保证 Apple 家庭会展示所有自定义数值设置。

风机 rpm、流量 L/min 和任意文字状态不能通过标准 HomeKit Bridge 原样展示在 Apple 家庭中，请使用 Home Assistant 仪表盘查看。不要将其伪装成湿度、照度等错误类型。

容器部署建议使用 host 网络，确保 mDNS 与 HomeKit 端口可被同一局域网访问。首次配对需在已登录目标 Apple 账号的 iPhone“家庭 → 添加配件”中扫描 HA 提供的二维码。

参考：[HomeKit Bridge 官方文档](https://www.home-assistant.io/integrations/homekit/)。协议核对来源：官方 AI 家智控 [GasWater 网页入口](https://ailink-appservice-h5-prd.hotwater.com.cn/dist/index.html#/GasWater)，核对日期 2026-09-02。

## 验证

`python -m unittest discover -s tests -v`：协议范围、非法输入、旧快照优先级和热水使用限制。安装 Home Assistant 后还会运行控制确认、错误传播、温控状态及三档映射测试；没有 HA 时这些运行时测试标记为跳过。

第三方项目，与 A.O. Smith 官方无隶属关系。许可证见 LICENSE。
