#!/bin/bash
set -e

# Release validation script for open-stocks-mcp
# This script validates that everything is ready for a release

echo "🔍 Open Stocks MCP Release Validation"
echo "===================================="

# Check if version argument is provided
if [ $# -eq 0 ]; then
    echo "❌ ERROR: Version argument required"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.1.7"
    exit 1
fi

TARGET_VERSION="$1"
echo "🎯 Target version: $TARGET_VERSION"

# Function to print error and exit
error_exit() {
    echo "❌ ERROR: $1"
    exit 1
}

# Function to print success
success() {
    echo "✅ $1"
}

# 1. Check working directory is clean
echo ""
echo "🔍 Checking working directory..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  WARNING: Working directory has uncommitted changes:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "Commit or stash changes before creating a release"
    fi
else
    success "Working directory is clean"
fi

# 2. Check if we're on main branch
echo ""
echo "🔍 Checking current branch..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  WARNING: Not on main branch (currently on: $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "Switch to main branch before creating a release"
    fi
else
    success "On main branch"
fi

# 3. Check version consistency
echo ""
echo "🔍 Checking version consistency..."

# Check pyproject.toml
PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [ "$PYPROJECT_VERSION" != "$TARGET_VERSION" ]; then
    error_exit "pyproject.toml version ($PYPROJECT_VERSION) doesn't match target ($TARGET_VERSION)"
fi
success "pyproject.toml version: $PYPROJECT_VERSION"

# Check __init__.py
INIT_VERSION=$(python -c "import sys; sys.path.insert(0, 'src'); from open_stocks_mcp import __version__; print(__version__)")
if [ "$INIT_VERSION" != "$TARGET_VERSION" ]; then
    error_exit "__init__.py version ($INIT_VERSION) doesn't match target ($TARGET_VERSION)"
fi
success "__init__.py version: $INIT_VERSION"

# 4. Check if tag already exists
echo ""
echo "🔍 Checking tag availability..."
if git tag -l | grep -q "^v$TARGET_VERSION$"; then
    error_exit "Tag v$TARGET_VERSION already exists"
fi
success "Tag v$TARGET_VERSION is available"

# 5. Test package build
echo ""
echo "🔍 Testing package build..."
if [ -d "dist" ]; then
    rm -rf dist/
fi

python -m build > /dev/null 2>&1 || error_exit "Package build failed"

# Check built files
WHEEL_FILE=$(ls dist/*.whl 2>/dev/null | head -n1)
SDIST_FILE=$(ls dist/*.tar.gz 2>/dev/null | head -n1)

if [ -z "$WHEEL_FILE" ]; then
    error_exit "No wheel file generated"
fi

if [ -z "$SDIST_FILE" ]; then
    error_exit "No source distribution generated"
fi

success "Package build successful"
success "Generated: $(basename "$WHEEL_FILE")"
success "Generated: $(basename "$SDIST_FILE")"

# 6. Verify wheel contents
echo ""
echo "🔍 Verifying wheel contents..."
WHEEL_VERSION=$(echo "$WHEEL_FILE" | sed -n 's/.*-\([0-9]\+\.[0-9]\+\.[0-9]\+\).*/\1/p')
if [ "$WHEEL_VERSION" != "$TARGET_VERSION" ]; then
    error_exit "Wheel version ($WHEEL_VERSION) doesn't match target ($TARGET_VERSION)"
fi

# Check if wheel contains source files
if ! unzip -l "$WHEEL_FILE" | grep -q "open_stocks_mcp.*\.py"; then
    error_exit "Wheel doesn't contain Python source files"
fi
success "Wheel contains source files"

# 7. Test package installation
echo ""
echo "🔍 Testing package installation..."
TEST_ENV=$(mktemp -d)
python -m venv "$TEST_ENV" > /dev/null 2>&1
source "$TEST_ENV/bin/activate"

pip install "$WHEEL_FILE" > /dev/null 2>&1 || error_exit "Package installation failed"

# Test import and version
INSTALLED_VERSION=$(python -c "import open_stocks_mcp; print(open_stocks_mcp.__version__)" 2>/dev/null)
if [ "$INSTALLED_VERSION" != "$TARGET_VERSION" ]; then
    deactivate
    rm -rf "$TEST_ENV"
    error_exit "Installed version ($INSTALLED_VERSION) doesn't match target ($TARGET_VERSION)"
fi

deactivate
rm -rf "$TEST_ENV"
success "Package installation test passed"

# 8. Check documentation references
echo ""
echo "🔍 Checking documentation references..."
if grep -r "v0\." README.md examples/Docker/README.md examples/Docker/Dockerfile | grep -v "v$TARGET_VERSION" | grep -q "v[0-9]"; then
    echo "⚠️  WARNING: Found documentation references to other versions:"
    grep -r "v0\." README.md examples/Docker/README.md examples/Docker/Dockerfile | grep -v "v$TARGET_VERSION" | grep "v[0-9]"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "Update documentation references before release"
    fi
else
    success "Documentation references are consistent"
fi

# 9. Final summary
echo ""
echo "🎉 Release Validation Summary"
echo "============================="
echo "✅ Version: $TARGET_VERSION"
echo "✅ Working directory: clean"
echo "✅ Branch: $CURRENT_BRANCH"
echo "✅ Version consistency: verified"
echo "✅ Tag availability: confirmed"
echo "✅ Package build: successful"
echo "✅ Package installation: tested"
echo "✅ Documentation: checked"
echo ""
echo "🚀 Ready to create release v$TARGET_VERSION!"
echo ""
echo "📋 Next steps:"
echo "   1. git tag v$TARGET_VERSION"
echo "   2. git push origin v$TARGET_VERSION"
echo "   3. gh release create v$TARGET_VERSION --title \"v$TARGET_VERSION - <description>\" --notes \"<release notes>\""
echo ""
echo "💡 Or use: gh release create v$TARGET_VERSION --generate-notes"

# Clean up
rm -rf dist/