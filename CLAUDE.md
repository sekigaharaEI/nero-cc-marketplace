# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal Claude Code plugin marketplace (`nero-cc-marketplace`) that hosts and distributes custom Claude Code plugins. The repository contains two main plugins:

1. **memory-stalker** (v1.0.6) - Memory management plugin with intelligent compression, traceable storage, and conversation resumption
2. **tt-pm-master** (v1.0.2) - Product manager toolkit with competitor analysis, PRD writing, business model planning, and NotebookLM integration

## Architecture

### Marketplace Structure

```
.claude-plugin/marketplace.json    # Marketplace manifest defining all plugins
plugins/
  ├── memory-stalker/              # Memory management plugin
  │   ├── .claude-plugin/plugin.json
  │   ├── commands/                # Command definitions (*.md files)
  │   ├── hooks/hooks.json         # PreCompact hook configuration
  │   ├── scripts/                 # Python scripts for memory operations
  │   └── prompts/                 # AI summary prompt templates
  └── tt-pm-master/                # Product manager plugin
      ├── .claude-plugin/plugin.json
      ├── commands/                # Command definitions
      └── skills/                  # Skill definitions (subdirectories)
```

### Plugin System

Each plugin follows the Claude Code plugin structure:
- **plugin.json**: Metadata (name, version, description, author, keywords)
- **commands/**: Markdown files defining slash commands
- **skills/**: Skill definitions for complex workflows
- **hooks/**: Event-based automation (e.g., PreCompact hook)
- **scripts/**: Implementation scripts (Python, shell, etc.)

### Key Components

**Marketplace Manifest** (`.claude-plugin/marketplace.json`):
- Defines marketplace metadata and owner
- Lists all available plugins with their source paths, versions, and tags
- Used by Claude Code to discover and install plugins

**Memory Stalker Hook System**:
- Uses PreCompact hook to automatically save conversation memory before context compression
- Executes `scripts/save_memory.py` which:
  - Parses the conversation transcript
  - Calls Anthropic API to generate AI summary
  - Saves structured memory file to `.claude/memories/`
  - Preserves last interaction round and task list

**Skills vs Commands**:
- Commands: Simple slash commands defined in markdown files
- Skills: Complex multi-step workflows with their own subdirectories

## Development Workflow

### Adding a New Plugin

1. Create plugin directory under `plugins/{plugin-name}/`
2. Add `.claude-plugin/plugin.json` with metadata (name, version, description, author, keywords)
3. Create `plugins/{plugin-name}/README.md` with complete documentation
4. Implement commands, skills, hooks, or scripts as needed
5. Register plugin in `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "plugin-name",
     "source": "./plugins/plugin-name",
     "description": "Plugin description",
     "version": "1.0.0",
     "tags": ["tag1", "tag2"]
   }
   ```
6. Update root `README.md`:
   - Add to "可用插件" table
   - Add detailed section under "插件详情" with hyperlink to plugin README

### README Documentation Standards

Every plugin must follow these documentation requirements:

1. **Plugin README**: Each plugin must have its own `plugins/{plugin-name}/README.md` with:
   - Feature descriptions
   - Installation instructions
   - Usage examples
   - Configuration details

2. **Root README Updates**: When adding or updating a plugin, update `README.md`:
   - Add entry to the "可用插件" (Available Plugins) table with version and description
   - Add detailed section under "插件详情" (Plugin Details) with:
     - Brief description
     - Feature list
     - Installation command
     - Usage examples
     - Hyperlink to plugin's README: `[查看详细文档](./plugins/{plugin-name}/README.md)`

### Updating Plugin Versions

When updating a plugin version, **ALL four files** must be updated synchronously:

1. `plugins/{plugin-name}/.claude-plugin/plugin.json` - U
2. pdate `"version"` field
3. `plugins/{plugin-name}/README.md` - Update version references if any
4. `README.md` (root) - Update version in "可用插件" table
5. `.claude-plugin/marketplace.json` - Update `"version"` field in plugins array

**Critical**: Version numbers must match exactly across all four files to avoid inconsistencies.

### Testing Plugins

Plugins are tested by:
1. Installing from the marketplace: `/plugin install {plugin-name}@nero-cc-marketplace`
2. Testing commands: `/command-name [args]`
3. Verifying hooks trigger correctly (e.g., PreCompact for memory-stalker)
4. Checking logs in `~/.claude/logs/` for errors

## Memory Stalker Implementation Details

**Python Dependencies**: Requires `anthropic>=0.18.0`

**Environment Variables**:
- `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (required)
- `ANTHROPIC_BASE_URL` (optional, for proxies)
- `ANTHROPIC_DEFAULT_SONNET_MODEL` (optional, defaults to claude-sonnet-4-20250514)

**Memory File Format**: Structured markdown with:
- Metadata (session ID, project path, timestamp, trigger type)
- Last complete interaction round (user input + assistant reply)
- Current task list
- AI-generated summary (task summary, code changes, key decisions, user preferences, follow-ups)

**Key Scripts**:
- `save_memory.py`: Main memory saving logic, triggered by PreCompact hook
- `list_memories.py`: Lists available memory files for `/memories` command
- `transcript_parser.py`: Parses conversation transcript JSON
- `check_env.py`: Environment validation for `/init` command
- `find_prompt_path.py`: Locates prompt template file for `/edit-memory-prompt`

## TT-PM-Master Implementation Details

**Skills Structure**: Each skill is a subdirectory under `skills/` containing:
- Skill definition files
- Prompt templates
- Supporting resources

**Available Skills**:
- Product management: competitor analysis, PRD writing, business model planning, product review
- NotebookLM integration: podcast/video/slides generation
- Utilities: session archiving, long text writing, document to slides conversion

## Important Notes

- The marketplace uses relative paths (`./plugins/...`) for plugin sources
- **Version Synchronization**: Plugin versions must be kept in sync across all four files: plugin.json, plugin README, root README, and marketplace.json
- **Documentation**: Every plugin requires its own README with a hyperlink from the root README
- Memory Stalker is a complete upgrade from the deprecated `custom-compact` plugin
- Hooks use `${CLAUDE_PLUGIN_ROOT}` variable to reference plugin installation directory
- Python scripts should handle encoding properly (UTF-8) to avoid character corruption
