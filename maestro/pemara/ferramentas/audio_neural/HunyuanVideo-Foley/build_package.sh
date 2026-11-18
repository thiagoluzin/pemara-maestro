#!/bin/bash
# 构建 HunyuanVideo-Foley Python 包的脚本

set -e  # 出现错误时退出

echo "🚀 开始构建 HunyuanVideo-Foley Python 包..."

# 清理之前的构建文件
echo "🧹 清理之前的构建文件..."
rm -rf build/ dist/ *.egg-info/

# 检查必要的工具
echo "🔍 检查构建工具..."
python -c "import setuptools, wheel; print('✅ setuptools和wheel已安装')" || {
    echo "❌ 请安装构建工具: pip install setuptools wheel"
    exit 1
}

# 检查setup.py
echo "🔍 验证setup.py配置..."
python setup.py check --restructuredtext --strict || {
    echo "⚠️  setup.py验证有警告，但继续构建..."
}

# 构建源码分发包
echo "📦 构建源码分发包..."
python setup.py sdist

# 构建wheel包
echo "🎡 构建wheel包..." 
python setup.py bdist_wheel

# 显示构建结果
echo "✅ 构建完成！生成的包："
ls -la dist/

# 验证包
echo "🔍 验证生成的包..."
python -m pip check dist/*.whl || echo "⚠️  包验证有警告"

echo ""
echo "📝 安装说明："
echo "# 从wheel文件安装:"
echo "pip install dist/hunyuanvideo_foley-1.0.0-py3-none-any.whl"
echo ""
echo "# 开发模式安装:"
echo "pip install -e ."
echo ""
echo "# 安装所有可选依赖:"
echo "pip install -e .[all]"
echo ""

echo "⚠️  注意：某些依赖需要单独安装："
echo "pip install git+https://github.com/descriptinc/audiotools"
echo "pip install git+https://github.com/huggingface/transformers@v4.49.0-SigLIP-2"

echo ""
echo "🎉 构建完成！查看 INSTALL.md 获取详细安装指南。"