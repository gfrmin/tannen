confirm() { local a; note_prompt; read -rp "$1 [y/N] " a; [[ "${a:-}" == [yY]* ]]; }
pause() { note_prompt; read -rp "   $1" _; }
