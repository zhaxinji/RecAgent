"""
RecAgent实验功能示例：创建和运行一个简单的PyTorch推荐系统实验
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.experiment import (
    create_experiment,
    generate_experiment_template,
    run_experiment,
    get_experiment_results,
)
from src.db.session import get_session
from src.models.user import get_user_by_email

async def main():
    print("RecAgent 实验功能示例")
    print("=" * 60)
    
    # 初始化数据库会话
    async with get_session() as session:
        # 获取用户ID (示例中使用测试用户)
        user = await get_user_by_email(session, "test@example.com")
        if not user:
            print("错误: 测试用户不存在，请先创建测试用户")
            return
        
        user_id = str(user.id)
        print(f"使用用户ID: {user_id}")
        
        # 步骤1: 生成一个实验模板
        print("\n步骤1: 生成实验模板")
        template_params = {
            "language": "python",
            "framework": "pytorch",
            "template_type": "recommender",
        }
        template_code = await generate_experiment_template(**template_params)
        print(f"已生成{len(template_code)}字节的模板代码")
        
        # 打印模板代码的一部分
        print("模板代码预览:")
        preview_lines = template_code.split('\n')[:10]
        print('\n'.join(preview_lines) + "\n... [代码省略] ...\n")
        
        # 步骤2: 创建一个实验
        print("\n步骤2: 创建实验")
        experiment_data = {
            "title": "基于PyTorch的矩阵分解推荐系统",
            "description": "使用PyTorch实现的简单矩阵分解模型，在MovieLens数据集上评估",
            "language": "python",
            "framework": "pytorch",
            "code": template_code,
            "user_id": user_id,
            "metadata": {
                "dataset": "MovieLens-100K",
                "model_type": "MatrixFactorization",
                "hyperparams": {
                    "embedding_dim": 100,
                    "lr": 0.01,
                    "epochs": 5
                }
            }
        }
        
        experiment = await create_experiment(**experiment_data)
        experiment_id = experiment["id"]
        print(f"实验已创建，ID: {experiment_id}")
        print(f"实验标题: {experiment['title']}")
        print(f"实验状态: {experiment['status']}")
        
        # 步骤3: 运行实验
        print("\n步骤3: 运行实验")
        print("开始执行实验代码...")
        run_result = await run_experiment(experiment_id, user_id)
        print(f"执行结果: {'成功' if run_result['success'] else '失败'}")
        
        if run_result['success']:
            print(f"实验执行时间: {run_result['execution_time']:.2f}秒")
            print("指标:")
            for metric, value in run_result['metrics'].items():
                print(f"  - {metric}: {value}")
        else:
            print(f"错误信息: {run_result['error']}")
        
        # 步骤4: 获取实验结果
        print("\n步骤4: 获取实验结果")
        results = await get_experiment_results(experiment_id, user_id)
        print(f"共有{len(results)}个结果")
        
        if results:
            latest_result = results[0]  # 最新的结果
            print(f"最新结果ID: {latest_result['id']}")
            print(f"创建时间: {latest_result['created_at']}")
            print(f"状态: {latest_result['status']}")
            
            if latest_result['output']:
                print("输出预览:")
                output_preview = latest_result['output'].split('\n')[:5]
                print('\n'.join(output_preview) + "\n... [输出省略] ...\n")

if __name__ == "__main__":
    asyncio.run(main()) 