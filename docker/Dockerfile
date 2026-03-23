# AgentHome Docker 镜像 - 开发模式
# 支持热更新，适合开发调试

# 使用包含 Node.js 和 Python 的镜像
FROM docker.1ms.run/nikolaik/python-nodejs:python3.12-nodejs20

# 设置 npm 国内镜像
RUN npm config set registry https://registry.npmmirror.com

# 设置 pip 国内镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
COPY frontend/package*.json ./frontend/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装前端依赖
RUN cd frontend && npm ci

# 复制项目代码
COPY . .

# 创建必要的目录
RUN mkdir -p data/uploads data/agents skills/installed rag/chroma_db rag/rag_document_lib

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# 暴露端口
EXPOSE 8000 3000

# 启动命令
CMD ["python", "main.py"]
