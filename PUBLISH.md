# Publishing Guide for AA Discord Onboarding

## GitHub Repository Setup

### 1. Create Repository on GitHub
1. Go to https://github.com/new
2. Repository name: `aa-discord-onboarding`
3. Description: "Discord onboarding plugin for Alliance Auth that streamlines EVE Online SSO integration"
4. Set to Public
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)

### 2. Push to GitHub
```bash
# Add the remote
git remote add origin https://github.com/cyberbalsa/aa-discord-onboarding.git

# Push the code
git branch -M main
git push -u origin main
```

### 3. Configure Repository Settings
1. Go to repository Settings
2. **General** → Features:
   - ✅ Issues
   - ✅ Wiki (optional)
   - ✅ Discussions (optional)
3. **Actions** → General:
   - ✅ Allow all actions and reusable workflows
4. **Pages** (optional):
   - Source: Deploy from a branch
   - Branch: main / docs (if you add documentation)

### 4. Set up PyPI Publishing (Optional)
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token (get from https://pypi.org/manage/account/token/)

## PyPI Publishing

### Manual Publishing
```bash
# Install publishing tools
pip install twine

# Build the package
python -m build

# Upload to PyPI
twine upload dist/*
```

### Automated Publishing via GitHub Actions
1. Create a new release on GitHub
2. Tag format: `v1.0.0`
3. The release workflow will automatically publish to PyPI

## Post-Publication

### 1. Update Alliance Auth Apps List
Submit a PR to add your plugin to:
- https://github.com/allianceauth/allianceauth/blob/master/docs/installation/apps/index.md

### 2. Community Announcement
- Post in Alliance Auth Discord
- Share on EVE Online subreddits (if appropriate)
- Update your corp/alliance documentation

## Package Information

- **Package Name**: `aa-discord-onboarding`
- **PyPI URL**: https://pypi.org/project/aa-discord-onboarding/
- **GitHub URL**: https://github.com/cyberbalsa/aa-discord-onboarding
- **Installation**: `pip install aa-discord-onboarding`

## Ready to Publish!

The package is fully prepared with:
✅ Clean, linted code
✅ Comprehensive documentation
✅ Test suite and CI/CD
✅ Proper packaging configuration
✅ GitHub workflows for automated testing and publishing
✅ Issue templates and contribution guidelines

Simply follow the steps above to publish to GitHub and PyPI!