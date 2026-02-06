# 积分系统数据库迁移指南

## 📋 迁移前准备

### 1. 确认Python环境
确保Python已正确安装并在PATH中：
```bash
python --version
```
应该显示类似 `Python 3.x.x` 的输出。

### 2. 数据库已备份
✅ 备份已创建：`db.sqlite3.backup_20260206`

如果你的数据库文件不在默认位置，请先手动备份：
```bash
# 在项目目录下
copy db.sqlite3 db.sqlite3.backup
```

---

## 🚀 方法一：使用批处理脚本（推荐）

### 最简单的方式 - 双击运行

1. **打开项目文件夹**
   ```
   c:\Users\GHUIQ\repos\EbbinghausAnywhere
   ```

2. **双击运行**
   - 找到 `run_migrations.bat` 文件
   - 双击运行
   - 脚本会自动执行所有迁移步骤

3. **查看结果**
   - 脚本会显示每一步的执行结果
   - 如果成功，会显示"所有迁移步骤已成功完成！"
   - 如果失败，会显示错误信息

---

## 🔧 方法二：手动执行命令

如果批处理脚本无法运行，可以手动执行以下命令：

### 步骤1：打开命令行工具

选择以下任一方式：
- **Windows PowerShell** (推荐)
- **命令提示符 (CMD)**
- **Git Bash** (如果可用)

### 步骤2：进入项目目录

```bash
cd c:\Users\GHUIQ\repos\EbbinghausAnywhere
```

### 步骤3：激活虚拟环境（如果使用）

如果你使用了虚拟环境，先激活它：

```bash
# 如果使用venv
.venv\Scripts\activate

# 或如果使用conda
conda activate your_env_name
```

### 步骤4：创建迁移文件

```bash
python manage.py makemigrations
```

**预期输出：**
```
Migrations for 'EAW':
  EAW/migrations/0001_initial_points_system.py
    - Create model UserPoints
    - Create model PointHistory
    - Create model UserPointsConfig
    - Create model PointRedemption
    - Create model UserStreak
```

### 步骤5：查看迁移SQL（可选）

如果想在应用前查看即将执行的SQL：

```bash
python manage.py sqlmigrate EAW 0001
```

### 步骤6：应用迁移

```bash
python manage.py migrate
```

**预期输出：**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, EAW, sessions
Running migrations:
  Applying EAW.0001_initial_points_system... OK
```

---

## ✅ 验证迁移成功

### 1. 检查数据库表

在Python shell中验证：
```bash
python manage.py shell
```

然后在shell中执行：
```python
from EAW.models import UserPoints, PointHistory, UserPointsConfig, PointRedemption, UserStreak

# 检查表是否创建成功
print("UserPoints:", UserPoints._meta.db_table)
print("PointHistory:", PointHistory._meta.db_table)
print("UserPointsConfig:", UserPointsConfig._meta.db_table)
print("PointRedemption:", PointRedemption._meta.db_table)
print("UserStreak:", UserStreak._meta.db_table)

# 退出shell
exit()
```

### 2. 检查迁移状态

```bash
python manage.py showmigrations EAW
```

应该显示类似：
```
[EAW]
 0001_initial_points_system
```

### 3. 启动开发服务器测试

```bash
python manage.py runserver
```

然后访问：
- 积分商城：http://localhost:8000/points/market/
- Admin后台：http://localhost:8000/admin/

---

## ❗ 常见问题

### 问题1：Python命令找不到

**错误信息：**
```
'python' 不是内部或外部命令，也不是可运行的程序
```

**解决方案：**
1. 确认Python已安装
2. 尝试使用 `py` 命令代替 `python`：
   ```bash
   py manage.py makemigrations
   py manage.py migrate
   ```
3. 或者使用 `python3`：
   ```bash
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```

### 问题2：权限错误

**错误信息：**
```
Permission denied: 'db.sqlite3'
```

**解决方案：**
1. 关闭所有可能使用数据库的程序（IDE、其他Python进程）
2. 确保对项目文件夹有写权限
3. 以管理员身份运行命令行

### 问题3：迁移冲突

**错误信息：**
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

**解决方案：**
1. 备份数据库
2. 删除迁移记录并重新创建：
   ```bash
   # 1. 备份数据库
   copy db.sqlite3 db.sqlite3.backup2

   # 2. 删除迁移文件
   del EAW\migrations\0001_*.py

   # 3. 重新创建迁移
   python manage.py makemigrations EAW --empty

   # 4. 应用迁移
   python manage.py migrate --fake-initial
   ```

### 问题4：模块导入错误

**错误信息：**
```
ModuleNotFoundError: No module named 'django'
```

**解决方案：**
1. 确认虚拟环境已激活
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔄 回滚迁移（如果需要）

如果迁移后发现问题需要回滚：

```bash
# 方法1：回滚到迁移前
python manage.py migrate EAW zero

# 方法2：从备份恢复
# 1. 停止服务器
# 2. 删除当前数据库
del db.sqlite3
# 3. 从备份恢复
copy db.sqlite3.backup_20260206 db.sqlite3
```

---

## 📞 获取帮助

如果遇到其他问题：

1. **查看Django日志**
   - 开发服务器会在终端显示详细错误信息

2. **查看迁移文件**
   - 检查 `EAW/migrations/0001_*.py` 文件内容

3. **Django文档**
   - https://docs.djangoproject.com/en/4.1/topics/migrations/

---

## ✨ 迁移成功后的下一步

### 1. 创建超级用户（如果还没有）
```bash
python manage.py createsuperuser
```

### 2. 启动服务器
```bash
python manage.py runserver
```

### 3. 测试积分系统
- 访问 http://localhost:8000/points/market/
- 测试复习获得积分
- 测试每日签到
- 测试兑换功能

### 4. 查看Admin后台
- 访问 http://localhost:8000/admin/
- 查看新增的积分相关模型：
  - User Points（用户积分）
  - Point History（积分历史）
  - User Points Config（积分配置）
  - Point Redemption（兑换记录）
  - User Streak（连续学习记录）

---

## 📊 迁移内容摘要

本次迁移会创建以下5个新表：

1. **EAW_userpoints** - 用户积分账户
   - 字段：user, current_points, total_earned, total_spent, last_updated

2. **EAW_pointhistory** - 积分历史记录
   - 字段：user, change_type, points, reason, reference_id, balance_after, created_at

3. **EAW_userpointsconfig** - 用户积分配置
   - 字段：user, minutes_per_point, redemption_step, min_redemption_minutes, max_redemption_minutes, daily_checkin_enabled, daily_checkin_points, streak_reward_enabled, streak_reward_points, streak_reward_days, created_at, updated_at

4. **EAW_pointredemption** - 兑换记录
   - 字段：user, points_spent, game_minutes, exchange_rate, status, notes, created_at

5. **EAW_userstreak** - 连续学习记录
   - 字段：user, current_streak, longest_streak, last_study_date, current_checkin_streak, longest_checkin_streak, last_checkin_date, last_streak_reward_date, updated_at

---

**祝迁移顺利！** 🎉
