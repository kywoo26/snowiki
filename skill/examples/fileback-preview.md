# Fileback Preview Example

Use this shape when a useful answer should become durable but still needs review.

```bash
snowiki fileback preview \
  "What is the Snowiki skill write policy?" \
  --answer-markdown "Durable writes must use reviewed fileback or CLI-mediated ingest/prune flows." \
  --summary "Reviewed write policy answer." \
  --evidence-path skill/SKILL.md \
  --queue \
  --output json
```

Treat the JSON output as a proposal until a documented fileback apply or queue apply path succeeds.
