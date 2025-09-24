#!/bin/bash
echo "Updating web-app subtree..."
git subtree pull --prefix=web-app https://github.com/ProximalEnergy/web-app dev --squash

echo "Updating api subtree..."
git subtree pull --prefix=api https://github.com/ProximalEnergy/api dev --squash

echo "All subtrees updated successfully!"
