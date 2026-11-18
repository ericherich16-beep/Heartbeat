# Project State Template

Agent Builder agents don't remember earlier chats, so the agent writes this block at every phase gate. The user saves it, for example in a Word document called `<App> - Project State` in their OneDrive project folder, and attaches or pastes it at the start of the next chat.

```text
PROJECT STATE
App:              <name>
Phase:            Grill | Spec | Slice | Build | Test | Complete
Current slice:    <n> of <total>   (status: building | verifying | importing | testing | done)
Last version:     <x.x.x.x>   (last imported version: <x.x.x.x>)
Files saved:      spec <yes/no>, lists.json <yes/no>, slice plan <yes/no>

Slices:
  1  <name>  - done (v1.0.1.0, tested <date>)
  2  <name>  - testing (v1.0.2.0)
  3  <name>  - not started

Durable decisions: publisher prefix <x>; env vars <names>; lists <names>; theme <colours>
Studio changes not yet in source: <none | list>
Open problems: <none | rule ID + description>
Next step: <exactly what the user or agent does next>
Notes: <anything else>
```

**Rules for the agent:**
- **Always output the full block,** not just the parts that changed.
- **"Next step" must be concrete,** for example "User imports v1.0.2.0 and runs slice 2 acceptance test", not "continue".
