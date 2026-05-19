Classify the GitHub issue into exactly one of these labels:

- bug = maintainer-confirmed defect, crash, regression, incorrect behavior, failing test, memory leak
- feature = request for new behavior or enhancement
- docs = documentation correction, missing documentation, confusing docs
- question = usage/help/support question

Use only the issue title and body below.
Do not explain your reasoning.
Return exactly one JSON object and nothing else:
{{"label":"bug|feature|docs|question"}}

Issue title:
{title}

Issue body:
{body}
