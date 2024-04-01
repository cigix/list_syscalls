#!/usr/bin/env python3

"""
html_output.py: Utilities to output the list of syscalls in HTML.
"""

def dump(syscalls):
    """dump(syscalls): Dump the syscalls' data to HTML.

    Args:
      - syscalls: list of SyscallDesc, the data about each syscall
    """
    with open("syscalls.html", "w") as f:
        f.write("""<!--
This table was generated automatically.
https://github.com/cigix/list_syscalls
-->
<table id="syscalls">
  <tr>
    <th>Number</th>
    <th>Name</th>
    <th>Kernel entrypoint</th>
    <th>Declarations</th>
  </tr>
""")
        for desc in syscalls:
            f.write("  <tr>\n")
            f.write(f"    <td>{desc.entry.number}</td>\n")
            f.write(f"    <td>{desc.entry.name}</td>\n")
            if desc.entry.entrypoint:
                f.write(f"    <td><code>{desc.entry.entrypoint}</code></td>\n")
            else:
                f.write(f"    <td></td>\n")
            f.write(f"    <td>\n")
            f.write(f"      <dl>\n")
            for decl in desc.decls:
                f.write(f"        <dt>{decl.origin}:</dt>\n")
                f.write(f"        <dd><code>{decl.decl}</code></dd>\n")
            f.write(f"      </dl>\n")
            f.write("    </td>\n")
            f.write("  </tr>\n")
        f.write("</table>\n")
