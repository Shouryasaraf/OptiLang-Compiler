"""Basic blocks and control-flow edges for the displayed three-address code."""

from __future__ import annotations


def cfg_lines(tac: list[str]) -> list[str]:
    sections: list[tuple[str, list[str]]] = [("main", [])]
    for instruction in tac:
        if instruction.startswith("function ") and instruction.endswith(":"):
            sections.append((instruction[9:-1], []))
        else:
            sections[-1][1].append(instruction)

    result: list[str] = []
    for name, instructions in sections:
        if not instructions:
            continue
        labels = {line[:-1]: index for index, line in enumerate(instructions)
                  if line.endswith(":")}
        leaders = {0}
        for index, line in enumerate(instructions):
            target = None
            if line.startswith("goto "):
                target = line[5:]
            elif line.startswith("if_false "):
                target = line.rsplit(" goto ", 1)[-1]
            if target is not None:
                leaders.add(labels[target])
                if index + 1 < len(instructions):
                    leaders.add(index + 1)
            elif line.startswith("return ") and index + 1 < len(instructions):
                leaders.add(index + 1)

        starts = sorted(leaders)
        result.append(f"{name}:")
        for block, start in enumerate(starts):
            end = starts[block + 1] if block + 1 < len(starts) else len(instructions)
            last = instructions[end - 1]
            successors: list[int] = []
            if last.startswith("goto "):
                successors.append(labels[last[5:]])
            elif last.startswith("if_false "):
                if end < len(instructions):
                    successors.append(end)
                successors.append(labels[last.rsplit(" goto ", 1)[-1]])
            elif not last.startswith("return ") and end < len(instructions):
                successors.append(end)
            result.append(f"  B{start} [{start}..{end - 1}] -> " +
                          (", ".join(f"B{target}" for target in successors) or "exit"))
    return result
