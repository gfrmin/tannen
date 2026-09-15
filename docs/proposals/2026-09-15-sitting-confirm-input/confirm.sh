# A key pressed while less closes or a gate runs sits in the terminal and becomes part of the
# NEXT answer: at the M4 sitting three typed "y"s were read as declines (D0251). So each prompt
# first discards what was typed before it appeared, and says so; and an answer is y/yes or n/no
# and nothing else — anything else, an empty line included, is shown back and asked again.
# Only on a terminal: the rehearsal harness feeds answers from a file, and draining a file
# would eat them.
drain_typeahead() {
    [ -t 0 ] || return 0
    local got= junk=
    while IFS= read -r -s -t 0.05 -n 4096 got; do junk+="$got"$'\n'; done
    junk+="$got"
    [ -z "$junk" ] || note "discarded keys typed before this prompt: $(printf '%q' "$junk")"
}
confirm() {
    local a
    note_prompt
    drain_typeahead
    while :; do
        IFS= read -rp "$1 [y/n] " a || return 1
        case "${a,,}" in
            y|yes) return 0 ;;
            n|no)  note "declined (you typed $(printf '%q' "$a"))"; return 1 ;;
            *)     note "not an answer: $(printf '%q' "$a") — type y or n" ;;
        esac
    done
}
pause() { note_prompt; drain_typeahead; read -rp "   $1" _; }
