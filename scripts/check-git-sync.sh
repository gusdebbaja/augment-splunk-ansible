#!/bin/bash

# check-git-sync.sh
# Quick script to verify git repository synchronization

set -e

MONOREPO_DIR="/tmp/splunk-apps-checkout"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 Checking Splunk Apps Git Repository Synchronization"
echo "=================================================="

# Check if repo exists
if [ ! -d "$MONOREPO_DIR" ]; then
    echo "❌ Repository not found at $MONOREPO_DIR"
    echo "   Run the main playbook first to clone the repository"
    exit 1
fi

cd "$MONOREPO_DIR"

# Display current state
echo ""
echo "📍 Current Repository State:"
echo "   Location: $(pwd)"
echo "   Remote URL: $(git remote get-url origin)"
echo "   Current Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "   HEAD Commit: $(git rev-parse --short HEAD)"
echo "   Last Commit: $(git log -1 --pretty=format:'%s (%an, %cr)')"

# Check if working directory is clean
echo ""
echo "🔄 Working Directory Status:"
if [ -z "$(git status --porcelain)" ]; then
    echo "   ✅ Working directory is clean"
else
    echo "   ⚠️  Working directory has changes:"
    git status --porcelain | sed 's/^/     /'
fi

# Check remote status
echo ""
echo "🌐 Remote Synchronization:"
echo "   Fetching latest from remote..."
git fetch origin --quiet

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/$(git rev-parse --abbrev-ref HEAD))

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "   ✅ Local repository is up to date with remote"
else
    echo "   ⚠️  Local repository is NOT up to date with remote"
    echo "   Local:  $LOCAL_COMMIT"
    echo "   Remote: $REMOTE_COMMIT"
    echo ""
    echo "   Recent remote commits not in local:"
    git log --oneline ${LOCAL_COMMIT}..${REMOTE_COMMIT} | head -5 | sed 's/^/     /'
fi

# Show recent commits
echo ""
echo "📝 Recent Commits (last 10):"
git log --oneline -10 | sed 's/^/   /'

# Check key directories
echo ""
echo "📁 Key Directories Check:"
for dir in common searchheads indexers heavy_forwarders universal_forwarders app-templates; do
    if [ -d "$dir" ]; then
        count=$(find "$dir" -type d -maxdepth 1 | wc -l)
        echo "   ✅ $dir/ ($((count-1)) items)"
    else
        echo "   ❌ $dir/ (not found)"
    fi
done

# Show last changes in each directory
echo ""
echo "🕐 Last Changes by Directory:"
for dir in common searchheads indexers heavy_forwarders universal_forwarders app-templates; do
    if [ -d "$dir" ]; then
        last_change=$(git log -1 --pretty=format:'%cr (%s)' -- "$dir/" 2>/dev/null || echo "No commits found")
        echo "   $dir/: $last_change"
    fi
done

echo ""
echo "🛠️  Quick Fix Commands:"
echo "   Force update: git reset --hard origin/\$(git rev-parse --abbrev-ref HEAD)"
echo "   Fresh clone: rm -rf $MONOREPO_DIR && git clone <repo-url> $MONOREPO_DIR"
echo "   Manual pull: cd $MONOREPO_DIR && git pull origin \$(git rev-parse --abbrev-ref HEAD)"

echo ""
echo "✅ Git sync check complete!"