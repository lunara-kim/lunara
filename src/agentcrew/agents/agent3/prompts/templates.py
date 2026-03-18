"""Agent 3 프롬프트 템플릿.

Selective Context 기반: build.gradle + 디렉토리 트리 + files_changed.
"""

SYSTEM_PROMPT = """\
You are a senior software engineer. You implement code based on task specifications.
You output ONLY the file contents in the specified format. No explanations.
"""

IMPLEMENT_TASK_PROMPT = """\
## Task
- ID: {task_id}
- Title: {task_title}
- Description: {task_description}
- Layer: {task_layer}
- Files to change: {files_changed}

## Project Context

### build.gradle
```
{build_gradle}
```

### Directory Tree
```
{directory_tree}
```

## Instructions
Implement the code for the task above.
For each file, output in this exact format:

===FILE: path/to/File.java===
<file contents>
===END_FILE===

Output ALL files listed in "Files to change". Follow the project conventions visible in the directory tree.
"""

FIX_BUILD_PROMPT = """\
## Build/Test Failed
The following build error occurred after implementing task {task_id}.

### Error Output
```
{error_output}
```

### Current Files
{current_files}

## Instructions
Fix the code to resolve the build/test errors.
Output the corrected files in the same format:

===FILE: path/to/File.java===
<corrected file contents>
===END_FILE===
"""
