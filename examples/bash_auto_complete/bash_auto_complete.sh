#!/bin/bash

function _bash_auto_complete() {
    local cur opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"

    opts=$(python auto_complete.py ${COMP_WORDS[@]})

    COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    return 0
}

complete -F _bash_auto_complete auto_complete.py