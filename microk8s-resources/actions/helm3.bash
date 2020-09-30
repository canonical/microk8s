# bash completion for helm                                 -*- shell-script -*-

__helm_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Homebrew on Macs have version 1.3 of bash-completion which doesn't include
# _init_completion. This is a very minimal version of that function.
__helm_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

__helm_index_of_word()
{
    local w word=$1
    shift
    index=0
    for w in "$@"; do
        [[ $w = "$word" ]] && return
        index=$((index+1))
    done
    index=-1
}

__helm_contains_word()
{
    local w word=$1; shift
    for w in "$@"; do
        [[ $w = "$word" ]] && return
    done
    return 1
}

__helm_handle_reply()
{
    __helm_debug "${FUNCNAME[0]}"
    case $cur in
        -*)
            if [[ $(type -t compopt) = "builtin" ]]; then
                compopt -o nospace
            fi
            local allflags
            if [ ${#must_have_one_flag[@]} -ne 0 ]; then
                allflags=("${must_have_one_flag[@]}")
            else
                allflags=("${flags[*]} ${two_word_flags[*]}")
            fi
            COMPREPLY=( $(compgen -W "${allflags[*]}" -- "$cur") )
            if [[ $(type -t compopt) = "builtin" ]]; then
                [[ "${COMPREPLY[0]}" == *= ]] || compopt +o nospace
            fi

            # complete after --flag=abc
            if [[ $cur == *=* ]]; then
                if [[ $(type -t compopt) = "builtin" ]]; then
                    compopt +o nospace
                fi

                local index flag
                flag="${cur%=*}"
                __helm_index_of_word "${flag}" "${flags_with_completion[@]}"
                COMPREPLY=()
                if [[ ${index} -ge 0 ]]; then
                    PREFIX=""
                    cur="${cur#*=}"
                    ${flags_completion[${index}]}
                    if [ -n "${ZSH_VERSION}" ]; then
                        # zsh completion needs --flag= prefix
                        eval "COMPREPLY=( \"\${COMPREPLY[@]/#/${flag}=}\" )"
                    fi
                fi
            fi
            return 0;
            ;;
    esac

    # check if we are handling a flag with special work handling
    local index
    __helm_index_of_word "${prev}" "${flags_with_completion[@]}"
    if [[ ${index} -ge 0 ]]; then
        ${flags_completion[${index}]}
        return
    fi

    # we are parsing a flag and don't have a special handler, no completion
    if [[ ${cur} != "${words[cword]}" ]]; then
        return
    fi

    local completions
    completions=("${commands[@]}")
    if [[ ${#must_have_one_noun[@]} -ne 0 ]]; then
        completions=("${must_have_one_noun[@]}")
    fi
    if [[ ${#must_have_one_flag[@]} -ne 0 ]]; then
        completions+=("${must_have_one_flag[@]}")
    fi
    COMPREPLY=( $(compgen -W "${completions[*]}" -- "$cur") )

    if [[ ${#COMPREPLY[@]} -eq 0 && ${#noun_aliases[@]} -gt 0 && ${#must_have_one_noun[@]} -ne 0 ]]; then
        COMPREPLY=( $(compgen -W "${noun_aliases[*]}" -- "$cur") )
    fi

    if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
		if declare -F __helm_custom_func >/dev/null; then
			# try command name qualified custom func
			__helm_custom_func
		else
			# otherwise fall back to unqualified for compatibility
			declare -F __custom_func >/dev/null && __custom_func
		fi
    fi

    # available in bash-completion >= 2, not always present on macOS
    if declare -F __ltrim_colon_completions >/dev/null; then
        __ltrim_colon_completions "$cur"
    fi

    # If there is only 1 completion and it is a flag with an = it will be completed
    # but we don't want a space after the =
    if [[ "${#COMPREPLY[@]}" -eq "1" ]] && [[ $(type -t compopt) = "builtin" ]] && [[ "${COMPREPLY[0]}" == --*= ]]; then
       compopt -o nospace
    fi
}

# The arguments should be in the form "ext1|ext2|extn"
__helm_handle_filename_extension_flag()
{
    local ext="$1"
    _filedir "@(${ext})"
}

__helm_handle_subdirs_in_dir_flag()
{
    local dir="$1"
    pushd "${dir}" >/dev/null 2>&1 && _filedir -d && popd >/dev/null 2>&1
}

__helm_handle_flag()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    # if a command required a flag, and we found it, unset must_have_one_flag()
    local flagname=${words[c]}
    local flagvalue
    # if the word contained an =
    if [[ ${words[c]} == *"="* ]]; then
        flagvalue=${flagname#*=} # take in as flagvalue after the =
        flagname=${flagname%=*} # strip everything after the =
        flagname="${flagname}=" # but put the = back
    fi
    __helm_debug "${FUNCNAME[0]}: looking for ${flagname}"
    if __helm_contains_word "${flagname}" "${must_have_one_flag[@]}"; then
        must_have_one_flag=()
    fi

    # if you set a flag which only applies to this command, don't show subcommands
    if __helm_contains_word "${flagname}" "${local_nonpersistent_flags[@]}"; then
      commands=()
    fi

    # keep flag value with flagname as flaghash
    # flaghash variable is an associative array which is only supported in bash > 3.
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        if [ -n "${flagvalue}" ] ; then
            flaghash[${flagname}]=${flagvalue}
        elif [ -n "${words[ $((c+1)) ]}" ] ; then
            flaghash[${flagname}]=${words[ $((c+1)) ]}
        else
            flaghash[${flagname}]="true" # pad "true" for bool flag
        fi
    fi

    # skip the argument to a two word flag
    if [[ ${words[c]} != *"="* ]] && __helm_contains_word "${words[c]}" "${two_word_flags[@]}"; then
			  __helm_debug "${FUNCNAME[0]}: found a flag ${words[c]}, skip the next argument"
        c=$((c+1))
        # if we are looking for a flags value, don't show commands
        if [[ $c -eq $cword ]]; then
            commands=()
        fi
    fi

    c=$((c+1))

}

__helm_handle_noun()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    if __helm_contains_word "${words[c]}" "${must_have_one_noun[@]}"; then
        must_have_one_noun=()
    elif __helm_contains_word "${words[c]}" "${noun_aliases[@]}"; then
        must_have_one_noun=()
    fi

    nouns+=("${words[c]}")
    c=$((c+1))
}

__helm_handle_command()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    local next_command
    if [[ -n ${last_command} ]]; then
        next_command="_${last_command}_${words[c]//:/__}"
    else
        if [[ $c -eq 0 ]]; then
            next_command="_helm_root_command"
        else
            next_command="_${words[c]//:/__}"
        fi
    fi
    c=$((c+1))
    __helm_debug "${FUNCNAME[0]}: looking for ${next_command}"
    declare -F "$next_command" >/dev/null && $next_command
}

__helm_handle_word()
{
    if [[ $c -ge $cword ]]; then
        __helm_handle_reply
        return
    fi
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    if [[ "${words[c]}" == -* ]]; then
        __helm_handle_flag
    elif __helm_contains_word "${words[c]}" "${commands[@]}"; then
        __helm_handle_command
    elif [[ $c -eq 0 ]]; then
        __helm_handle_command
    elif __helm_contains_word "${words[c]}" "${command_aliases[@]}"; then
        # aliashash variable is an associative array which is only supported in bash > 3.
        if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
            words[c]=${aliashash[${words[c]}]}
            __helm_handle_command
        else
            __helm_handle_noun
        fi
    else
        __helm_handle_noun
    fi
    __helm_handle_word
}


__helm_override_flag_list=(--kubeconfig --kube-context --namespace -n)
__helm_override_flags()
{
    local ${__helm_override_flag_list[*]##*-} two_word_of of var
    for w in "${words[@]}"; do
        if [ -n "${two_word_of}" ]; then
            eval "${two_word_of##*-}=\"${two_word_of}=\${w}\""
            two_word_of=
            continue
        fi
        for of in "${__helm_override_flag_list[@]}"; do
            case "${w}" in
                ${of}=*)
                    eval "${of##*-}=\"${w}\""
                    ;;
                ${of})
                    two_word_of="${of}"
                    ;;
            esac
        done
    done
    for var in "${__helm_override_flag_list[@]##*-}"; do
        if eval "test -n \"\$${var}\""; then
            eval "echo \${${var}}"
        fi
    done
}

__helm_override_flags_to_kubectl_flags()
{
    # --kubeconfig, -n, --namespace stay the same for kubectl
    # --kube-context becomes --context for kubectl
    __helm_debug "${FUNCNAME[0]}: flags to convert: $1"
    echo "$1" | sed s/kube-context/context/
}

__helm_get_repos()
{
    eval $(__helm_binary_name) repo list 2>/dev/null | tail +2 | cut -f1
}

__helm_get_contexts()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    local template out
    template="{{ range .contexts  }}{{ .name }} {{ end }}"
    if out=$(kubectl config -o template --template="${template}" view 2>/dev/null); then
        COMPREPLY=( $( compgen -W "${out[*]}" -- "$cur" ) )
    fi
}

__helm_get_namespaces()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    local template out
    template="{{ range .items  }}{{ .metadata.name }} {{ end }}"

    flags=$(__helm_override_flags_to_kubectl_flags "$(__helm_override_flags)")
    __helm_debug "${FUNCNAME[0]}: override flags for kubectl are: $flags"

    # Must use eval in case the flags contain a variable such as $HOME
    if out=$(eval kubectl get ${flags} -o template --template=\"${template}\" namespace 2>/dev/null); then
        COMPREPLY+=( $( compgen -W "${out[*]}" -- "$cur" ) )
    fi
}

__helm_output_options()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    COMPREPLY+=( $( compgen -W "table json yaml" -- "$cur" ) )
}

__helm_binary_name()
{
    local helm_binary
    helm_binary="${words[0]}"
    __helm_debug "${FUNCNAME[0]}: helm_binary is ${helm_binary}"
    echo ${helm_binary}
}

# This function prevents the zsh shell from adding a space after
# a completion by adding a second, fake completion
__helm_zsh_comp_nospace() {
    __helm_debug "${FUNCNAME[0]}: in is ${in[*]}"

    local out in=("$@")

    # The shell will normally add a space after these completions.
    # To avoid that we should use "compopt -o nospace".  However, it is not
    # available in zsh.
    # Instead, we trick the shell by pretending there is a second, longer match.
    # We only do this if there is a single choice left for completion
    # to reduce the times the user could be presented with the fake completion choice.

    out=($(echo ${in[*]} | tr " " "\n" | \grep "^${cur}"))
    __helm_debug "${FUNCNAME[0]}: out is ${out[*]}"

    [ ${#out[*]} -eq 1 ] && out+=("${out}.")

    __helm_debug "${FUNCNAME[0]}: out is now ${out[*]}"

    echo "${out[*]}"
}

# $1 = 1 if the completion should include local charts (which means file completion)
__helm_list_charts()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    local repo url file out=() nospace=0 wantFiles=$1

    # Handle completions for repos
    for repo in $(__helm_get_repos); do
        if [[ "${cur}" =~ ^${repo}/.* ]]; then
            # We are doing completion from within a repo
            out=$(eval $(__helm_binary_name) search repo ${cur} 2>/dev/null | cut -f1 | \grep ^${cur})
            nospace=0
        elif [[ ${repo} =~ ^${cur}.* ]]; then
            # We are completing a repo name
            out+=(${repo}/)
            nospace=1
        fi
    done
    __helm_debug "${FUNCNAME[0]}: out after repos is ${out[*]}"

    # Handle completions for url prefixes
    for url in https:// http:// file://; do
        if [[ "${cur}" =~ ^${url}.* ]]; then
            # The user already put in the full url prefix.  Return it
            # back as a completion to avoid the shell doing path completion
            out="${cur}"
            nospace=1
        elif [[ ${url} =~ ^${cur}.* ]]; then
            # We are completing a url prefix
            out+=(${url})
            nospace=1
        fi
    done
    __helm_debug "${FUNCNAME[0]}: out after urls is ${out[*]}"

    # Handle completion for files.
    # We only do this if:
    #   1- There are other completions found (if there are no completions,
    #      the shell will do file completion itself)
    #   2- If there is some input from the user (or else we will end up
    #      lising the entire content of the current directory which will
    #      be too many choices for the user to find the real repos)
    if [ $wantFiles -eq 1 ] && [ -n "${out[*]}" ] && [ -n "${cur}" ]; then
        for file in $(\ls); do
            if [[ ${file} =~ ^${cur}.* ]]; then
                # We are completing a file prefix
                out+=(${file})
                nospace=1
            fi
        done
    fi
    __helm_debug "${FUNCNAME[0]}: out after files is ${out[*]}"

    # If the user didn't provide any input to completion,
    # we provide a hint that a path can also be used
    [ $wantFiles -eq 1 ] && [ -z "${cur}" ] && out+=(./ /)

    __helm_debug "${FUNCNAME[0]}: out after checking empty input is ${out[*]}"

    if [ $nospace -eq 1 ]; then
        if [[ -n "${ZSH_VERSION}" ]]; then
            # Don't let the shell add a space after the completion
            local tmpout=$(__helm_zsh_comp_nospace "${out[@]}")
            unset out
            out=$tmpout
        elif [[ $(type -t compopt) = "builtin" ]]; then
            compopt -o nospace
        fi
    fi

    __helm_debug "${FUNCNAME[0]}: final out is ${out[*]}"
    COMPREPLY=( $( compgen -W "${out[*]}" -- "$cur" ) )
}

__helm_list_releases()
{
	__helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
	local out filter
	# Use ^ to map from the start of the release name
	filter="^${words[c]}"
    # Use eval in case helm_binary_name or __helm_override_flags contains a variable (e.g., $HOME/bin/h3)
    if out=$(eval $(__helm_binary_name) list $(__helm_override_flags) -a -q -m 1000 -f ${filter} 2>/dev/null); then
        COMPREPLY=( $( compgen -W "${out[*]}" -- "$cur" ) )
    fi
}

__helm_list_repos()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    local out
    # Use eval in case helm_binary_name contains a variable (e.g., $HOME/bin/h3)
    if out=$(__helm_get_repos); then
        COMPREPLY=( $( compgen -W "${out[*]}" -- "$cur" ) )
    fi
}

__helm_list_plugins()
{
    __helm_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    local out
    # Use eval in case helm_binary_name contains a variable (e.g., $HOME/bin/h3)
    if out=$(eval $(__helm_binary_name) plugin list 2>/dev/null | tail +2 | cut -f1); then
        COMPREPLY=( $( compgen -W "${out[*]}" -- "$cur" ) )
    fi
}

__helm_list_charts_after_name() {
    __helm_debug "${FUNCNAME[0]}: last_command is $last_command"
    if [[ ${#nouns[@]} -eq 1 ]]; then
        __helm_list_charts 1
    fi
}

__helm_list_releases_then_charts() {
    __helm_debug "${FUNCNAME[0]}: last_command is $last_command"
    if [[ ${#nouns[@]} -eq 0 ]]; then
        __helm_list_releases
    elif [[ ${#nouns[@]} -eq 1 ]]; then
        __helm_list_charts 1
    fi
}

__helm_custom_func()
{
    __helm_debug "${FUNCNAME[0]}: last_command is $last_command"
    case ${last_command} in
        helm_pull)
            __helm_list_charts 0
            return
            ;;
        helm_show_*)
            __helm_list_charts 1
            return
            ;;
        helm_install | helm_template)
            __helm_list_charts_after_name
            return
            ;;
        helm_upgrade)
            __helm_list_releases_then_charts
            return
            ;;
        helm_uninstall | helm_history | helm_status | helm_test |\
        helm_rollback | helm_get_*)
            __helm_list_releases
            return
            ;;
        helm_repo_remove)
            __helm_list_repos
            return
            ;;
        helm_plugin_uninstall | helm_plugin_update)
            __helm_list_plugins
            return
            ;;
        *)
            ;;
    esac
}

_helm_completion()
{
    last_command="helm_completion"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--help")
    flags+=("-h")
    local_nonpersistent_flags+=("--help")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    must_have_one_noun+=("bash")
    must_have_one_noun+=("zsh")
    noun_aliases=()
}

_helm_create()
{
    last_command="helm_create"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--starter=")
    two_word_flags+=("--starter")
    two_word_flags+=("-p")
    local_nonpersistent_flags+=("--starter=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_dependency_build()
{
    last_command="helm_dependency_build"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_dependency_list()
{
    last_command="helm_dependency_list"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_dependency_update()
{
    last_command="helm_dependency_update"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--skip-refresh")
    local_nonpersistent_flags+=("--skip-refresh")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_dependency()
{
    last_command="helm_dependency"

    command_aliases=()

    commands=()
    commands+=("build")
    commands+=("list")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("ls")
        aliashash["ls"]="list"
    fi
    commands+=("update")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("up")
        aliashash["up"]="update"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_env()
{
    last_command="helm_env"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get_all()
{
    last_command="helm_get_all"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--revision=")
    two_word_flags+=("--revision")
    local_nonpersistent_flags+=("--revision=")
    flags+=("--template=")
    two_word_flags+=("--template")
    local_nonpersistent_flags+=("--template=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get_hooks()
{
    last_command="helm_get_hooks"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--revision=")
    two_word_flags+=("--revision")
    local_nonpersistent_flags+=("--revision=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get_manifest()
{
    last_command="helm_get_manifest"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--revision=")
    two_word_flags+=("--revision")
    local_nonpersistent_flags+=("--revision=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get_notes()
{
    last_command="helm_get_notes"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--revision=")
    two_word_flags+=("--revision")
    local_nonpersistent_flags+=("--revision=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get_values()
{
    last_command="helm_get_values"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--all")
    flags+=("-a")
    local_nonpersistent_flags+=("--all")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--revision=")
    two_word_flags+=("--revision")
    local_nonpersistent_flags+=("--revision=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_get()
{
    last_command="helm_get"

    command_aliases=()

    commands=()
    commands+=("all")
    commands+=("hooks")
    commands+=("manifest")
    commands+=("notes")
    commands+=("values")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_history()
{
    last_command="helm_history"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--max=")
    two_word_flags+=("--max")
    local_nonpersistent_flags+=("--max=")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_install()
{
    last_command="helm_install"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--atomic")
    local_nonpersistent_flags+=("--atomic")
    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--dependency-update")
    local_nonpersistent_flags+=("--dependency-update")
    flags+=("--devel")
    local_nonpersistent_flags+=("--devel")
    flags+=("--dry-run")
    local_nonpersistent_flags+=("--dry-run")
    flags+=("--generate-name")
    flags+=("-g")
    local_nonpersistent_flags+=("--generate-name")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--name-template=")
    two_word_flags+=("--name-template")
    local_nonpersistent_flags+=("--name-template=")
    flags+=("--no-hooks")
    local_nonpersistent_flags+=("--no-hooks")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--render-subchart-notes")
    local_nonpersistent_flags+=("--render-subchart-notes")
    flags+=("--replace")
    local_nonpersistent_flags+=("--replace")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--set=")
    two_word_flags+=("--set")
    local_nonpersistent_flags+=("--set=")
    flags+=("--set-file=")
    two_word_flags+=("--set-file")
    local_nonpersistent_flags+=("--set-file=")
    flags+=("--set-string=")
    two_word_flags+=("--set-string")
    local_nonpersistent_flags+=("--set-string=")
    flags+=("--skip-crds")
    local_nonpersistent_flags+=("--skip-crds")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--values=")
    two_word_flags+=("--values")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--values=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--wait")
    local_nonpersistent_flags+=("--wait")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_lint()
{
    last_command="helm_lint"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--set=")
    two_word_flags+=("--set")
    local_nonpersistent_flags+=("--set=")
    flags+=("--set-file=")
    two_word_flags+=("--set-file")
    local_nonpersistent_flags+=("--set-file=")
    flags+=("--set-string=")
    two_word_flags+=("--set-string")
    local_nonpersistent_flags+=("--set-string=")
    flags+=("--strict")
    local_nonpersistent_flags+=("--strict")
    flags+=("--values=")
    two_word_flags+=("--values")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--values=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_list()
{
    last_command="helm_list"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--all")
    flags+=("-a")
    local_nonpersistent_flags+=("--all")
    flags+=("--all-namespaces")
    local_nonpersistent_flags+=("--all-namespaces")
    flags+=("--date")
    flags+=("-d")
    local_nonpersistent_flags+=("--date")
    flags+=("--deployed")
    local_nonpersistent_flags+=("--deployed")
    flags+=("--failed")
    local_nonpersistent_flags+=("--failed")
    flags+=("--filter=")
    two_word_flags+=("--filter")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--filter=")
    flags+=("--max=")
    two_word_flags+=("--max")
    two_word_flags+=("-m")
    local_nonpersistent_flags+=("--max=")
    flags+=("--offset=")
    two_word_flags+=("--offset")
    local_nonpersistent_flags+=("--offset=")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--pending")
    local_nonpersistent_flags+=("--pending")
    flags+=("--reverse")
    flags+=("-r")
    local_nonpersistent_flags+=("--reverse")
    flags+=("--short")
    flags+=("-q")
    local_nonpersistent_flags+=("--short")
    flags+=("--superseded")
    local_nonpersistent_flags+=("--superseded")
    flags+=("--uninstalled")
    local_nonpersistent_flags+=("--uninstalled")
    flags+=("--uninstalling")
    local_nonpersistent_flags+=("--uninstalling")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_package()
{
    last_command="helm_package"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--app-version=")
    two_word_flags+=("--app-version")
    local_nonpersistent_flags+=("--app-version=")
    flags+=("--dependency-update")
    flags+=("-u")
    local_nonpersistent_flags+=("--dependency-update")
    flags+=("--destination=")
    two_word_flags+=("--destination")
    two_word_flags+=("-d")
    local_nonpersistent_flags+=("--destination=")
    flags+=("--key=")
    two_word_flags+=("--key")
    local_nonpersistent_flags+=("--key=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--set=")
    two_word_flags+=("--set")
    local_nonpersistent_flags+=("--set=")
    flags+=("--set-file=")
    two_word_flags+=("--set-file")
    local_nonpersistent_flags+=("--set-file=")
    flags+=("--set-string=")
    two_word_flags+=("--set-string")
    local_nonpersistent_flags+=("--set-string=")
    flags+=("--sign")
    local_nonpersistent_flags+=("--sign")
    flags+=("--values=")
    two_word_flags+=("--values")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--values=")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_plugin_install()
{
    last_command="helm_plugin_install"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_plugin_list()
{
    last_command="helm_plugin_list"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_plugin_uninstall()
{
    last_command="helm_plugin_uninstall"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_plugin_update()
{
    last_command="helm_plugin_update"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_plugin()
{
    last_command="helm_plugin"

    command_aliases=()

    commands=()
    commands+=("install")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("add")
        aliashash["add"]="install"
    fi
    commands+=("list")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("ls")
        aliashash["ls"]="list"
    fi
    commands+=("uninstall")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("remove")
        aliashash["remove"]="uninstall"
        command_aliases+=("rm")
        aliashash["rm"]="uninstall"
    fi
    commands+=("update")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("up")
        aliashash["up"]="update"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_pull()
{
    last_command="helm_pull"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--destination=")
    two_word_flags+=("--destination")
    two_word_flags+=("-d")
    local_nonpersistent_flags+=("--destination=")
    flags+=("--devel")
    local_nonpersistent_flags+=("--devel")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--prov")
    local_nonpersistent_flags+=("--prov")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--untar")
    local_nonpersistent_flags+=("--untar")
    flags+=("--untardir=")
    two_word_flags+=("--untardir")
    local_nonpersistent_flags+=("--untardir=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo_add()
{
    last_command="helm_repo_add"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--no-update")
    local_nonpersistent_flags+=("--no-update")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo_index()
{
    last_command="helm_repo_index"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--merge=")
    two_word_flags+=("--merge")
    local_nonpersistent_flags+=("--merge=")
    flags+=("--url=")
    two_word_flags+=("--url")
    local_nonpersistent_flags+=("--url=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo_list()
{
    last_command="helm_repo_list"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo_remove()
{
    last_command="helm_repo_remove"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo_update()
{
    last_command="helm_repo_update"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_repo()
{
    last_command="helm_repo"

    command_aliases=()

    commands=()
    commands+=("add")
    commands+=("index")
    commands+=("list")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("ls")
        aliashash["ls"]="list"
    fi
    commands+=("remove")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("rm")
        aliashash["rm"]="remove"
    fi
    commands+=("update")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("up")
        aliashash["up"]="update"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_rollback()
{
    last_command="helm_rollback"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--cleanup-on-fail")
    local_nonpersistent_flags+=("--cleanup-on-fail")
    flags+=("--dry-run")
    local_nonpersistent_flags+=("--dry-run")
    flags+=("--force")
    local_nonpersistent_flags+=("--force")
    flags+=("--no-hooks")
    local_nonpersistent_flags+=("--no-hooks")
    flags+=("--recreate-pods")
    local_nonpersistent_flags+=("--recreate-pods")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--wait")
    local_nonpersistent_flags+=("--wait")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_search_hub()
{
    last_command="helm_search_hub"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--endpoint=")
    two_word_flags+=("--endpoint")
    local_nonpersistent_flags+=("--endpoint=")
    flags+=("--max-col-width=")
    two_word_flags+=("--max-col-width")
    local_nonpersistent_flags+=("--max-col-width=")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_search_repo()
{
    last_command="helm_search_repo"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--devel")
    local_nonpersistent_flags+=("--devel")
    flags+=("--max-col-width=")
    two_word_flags+=("--max-col-width")
    local_nonpersistent_flags+=("--max-col-width=")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--regexp")
    flags+=("-r")
    local_nonpersistent_flags+=("--regexp")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--versions")
    flags+=("-l")
    local_nonpersistent_flags+=("--versions")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_search()
{
    last_command="helm_search"

    command_aliases=()

    commands=()
    commands+=("hub")
    commands+=("repo")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_show_all()
{
    last_command="helm_show_all"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_show_chart()
{
    last_command="helm_show_chart"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_show_readme()
{
    last_command="helm_show_readme"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_show_values()
{
    last_command="helm_show_values"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_show()
{
    last_command="helm_show"

    command_aliases=()

    commands=()
    commands+=("all")
    commands+=("chart")
    commands+=("readme")
    commands+=("values")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_status()
{
    last_command="helm_status"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--revision=")
    two_word_flags+=("--revision")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_template()
{
    last_command="helm_template"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--api-versions=")
    two_word_flags+=("--api-versions")
    two_word_flags+=("-a")
    local_nonpersistent_flags+=("--api-versions=")
    flags+=("--atomic")
    local_nonpersistent_flags+=("--atomic")
    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--dependency-update")
    local_nonpersistent_flags+=("--dependency-update")
    flags+=("--devel")
    local_nonpersistent_flags+=("--devel")
    flags+=("--dry-run")
    local_nonpersistent_flags+=("--dry-run")
    flags+=("--generate-name")
    flags+=("-g")
    local_nonpersistent_flags+=("--generate-name")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--name-template=")
    two_word_flags+=("--name-template")
    local_nonpersistent_flags+=("--name-template=")
    flags+=("--no-hooks")
    local_nonpersistent_flags+=("--no-hooks")
    flags+=("--output-dir=")
    two_word_flags+=("--output-dir")
    local_nonpersistent_flags+=("--output-dir=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--render-subchart-notes")
    local_nonpersistent_flags+=("--render-subchart-notes")
    flags+=("--replace")
    local_nonpersistent_flags+=("--replace")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--set=")
    two_word_flags+=("--set")
    local_nonpersistent_flags+=("--set=")
    flags+=("--set-file=")
    two_word_flags+=("--set-file")
    local_nonpersistent_flags+=("--set-file=")
    flags+=("--set-string=")
    two_word_flags+=("--set-string")
    local_nonpersistent_flags+=("--set-string=")
    flags+=("--show-only=")
    two_word_flags+=("--show-only")
    two_word_flags+=("-s")
    local_nonpersistent_flags+=("--show-only=")
    flags+=("--skip-crds")
    local_nonpersistent_flags+=("--skip-crds")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--validate")
    local_nonpersistent_flags+=("--validate")
    flags+=("--values=")
    two_word_flags+=("--values")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--values=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--wait")
    local_nonpersistent_flags+=("--wait")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_test()
{
    last_command="helm_test"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--logs")
    local_nonpersistent_flags+=("--logs")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_uninstall()
{
    last_command="helm_uninstall"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--dry-run")
    local_nonpersistent_flags+=("--dry-run")
    flags+=("--keep-history")
    local_nonpersistent_flags+=("--keep-history")
    flags+=("--no-hooks")
    local_nonpersistent_flags+=("--no-hooks")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_upgrade()
{
    last_command="helm_upgrade"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--atomic")
    local_nonpersistent_flags+=("--atomic")
    flags+=("--ca-file=")
    two_word_flags+=("--ca-file")
    local_nonpersistent_flags+=("--ca-file=")
    flags+=("--cert-file=")
    two_word_flags+=("--cert-file")
    local_nonpersistent_flags+=("--cert-file=")
    flags+=("--cleanup-on-fail")
    local_nonpersistent_flags+=("--cleanup-on-fail")
    flags+=("--devel")
    local_nonpersistent_flags+=("--devel")
    flags+=("--dry-run")
    local_nonpersistent_flags+=("--dry-run")
    flags+=("--force")
    local_nonpersistent_flags+=("--force")
    flags+=("--history-max=")
    two_word_flags+=("--history-max")
    local_nonpersistent_flags+=("--history-max=")
    flags+=("--install")
    flags+=("-i")
    local_nonpersistent_flags+=("--install")
    flags+=("--key-file=")
    two_word_flags+=("--key-file")
    local_nonpersistent_flags+=("--key-file=")
    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--no-hooks")
    local_nonpersistent_flags+=("--no-hooks")
    flags+=("--output=")
    two_word_flags+=("--output")
    flags_with_completion+=("--output")
    flags_completion+=("__helm_output_options")
    two_word_flags+=("-o")
    flags_with_completion+=("-o")
    flags_completion+=("__helm_output_options")
    local_nonpersistent_flags+=("--output=")
    flags+=("--password=")
    two_word_flags+=("--password")
    local_nonpersistent_flags+=("--password=")
    flags+=("--render-subchart-notes")
    local_nonpersistent_flags+=("--render-subchart-notes")
    flags+=("--repo=")
    two_word_flags+=("--repo")
    local_nonpersistent_flags+=("--repo=")
    flags+=("--reset-values")
    local_nonpersistent_flags+=("--reset-values")
    flags+=("--reuse-values")
    local_nonpersistent_flags+=("--reuse-values")
    flags+=("--set=")
    two_word_flags+=("--set")
    local_nonpersistent_flags+=("--set=")
    flags+=("--set-file=")
    two_word_flags+=("--set-file")
    local_nonpersistent_flags+=("--set-file=")
    flags+=("--set-string=")
    two_word_flags+=("--set-string")
    local_nonpersistent_flags+=("--set-string=")
    flags+=("--timeout=")
    two_word_flags+=("--timeout")
    local_nonpersistent_flags+=("--timeout=")
    flags+=("--username=")
    two_word_flags+=("--username")
    local_nonpersistent_flags+=("--username=")
    flags+=("--values=")
    two_word_flags+=("--values")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--values=")
    flags+=("--verify")
    local_nonpersistent_flags+=("--verify")
    flags+=("--version=")
    two_word_flags+=("--version")
    local_nonpersistent_flags+=("--version=")
    flags+=("--wait")
    local_nonpersistent_flags+=("--wait")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_verify()
{
    last_command="helm_verify"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--keyring=")
    two_word_flags+=("--keyring")
    local_nonpersistent_flags+=("--keyring=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_version()
{
    last_command="helm_version"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--short")
    local_nonpersistent_flags+=("--short")
    flags+=("--template=")
    two_word_flags+=("--template")
    local_nonpersistent_flags+=("--template=")
    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_helm_root_command()
{
    last_command="helm"

    command_aliases=()

    commands=()
    commands+=("completion")
    commands+=("create")
    commands+=("dependency")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("dep")
        aliashash["dep"]="dependency"
        command_aliases+=("dependencies")
        aliashash["dependencies"]="dependency"
    fi
    commands+=("env")
    commands+=("get")
    commands+=("history")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("hist")
        aliashash["hist"]="history"
    fi
    commands+=("install")
    commands+=("lint")
    commands+=("list")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("ls")
        aliashash["ls"]="list"
    fi
    commands+=("package")
    commands+=("plugin")
    commands+=("pull")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("fetch")
        aliashash["fetch"]="pull"
    fi
    commands+=("repo")
    commands+=("rollback")
    commands+=("search")
    commands+=("show")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("inspect")
        aliashash["inspect"]="show"
    fi
    commands+=("status")
    commands+=("template")
    commands+=("test")
    commands+=("uninstall")
    if [[ -z "${BASH_VERSION}" || "${BASH_VERSINFO[0]}" -gt 3 ]]; then
        command_aliases+=("del")
        aliashash["del"]="uninstall"
        command_aliases+=("delete")
        aliashash["delete"]="uninstall"
        command_aliases+=("un")
        aliashash["un"]="uninstall"
    fi
    commands+=("upgrade")
    commands+=("verify")
    commands+=("version")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--add-dir-header")
    flags+=("--alsologtostderr")
    flags+=("--debug")
    flags+=("--kube-context=")
    two_word_flags+=("--kube-context")
    flags_with_completion+=("--kube-context")
    flags_completion+=("__helm_get_contexts")
    flags+=("--kubeconfig=")
    two_word_flags+=("--kubeconfig")
    flags+=("--log-backtrace-at=")
    two_word_flags+=("--log-backtrace-at")
    flags+=("--log-dir=")
    two_word_flags+=("--log-dir")
    flags+=("--log-file=")
    two_word_flags+=("--log-file")
    flags+=("--log-file-max-size=")
    two_word_flags+=("--log-file-max-size")
    flags+=("--logtostderr")
    flags+=("--namespace=")
    two_word_flags+=("--namespace")
    flags_with_completion+=("--namespace")
    flags_completion+=("__helm_get_namespaces")
    two_word_flags+=("-n")
    flags_with_completion+=("-n")
    flags_completion+=("__helm_get_namespaces")
    flags+=("--registry-config=")
    two_word_flags+=("--registry-config")
    flags+=("--repository-cache=")
    two_word_flags+=("--repository-cache")
    flags+=("--repository-config=")
    two_word_flags+=("--repository-config")
    flags+=("--skip-headers")
    flags+=("--skip-log-headers")
    flags+=("--stderrthreshold=")
    two_word_flags+=("--stderrthreshold")
    flags+=("--v=")
    two_word_flags+=("--v")
    two_word_flags+=("-v")
    flags+=("--vmodule=")
    two_word_flags+=("--vmodule")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

__start_helm()
{
    local cur prev words cword
    declare -A flaghash 2>/dev/null || :
    declare -A aliashash 2>/dev/null || :
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion -s || return
    else
        __helm_init_completion -n "=" || return
    fi

    local c=0
    local flags=()
    local two_word_flags=()
    local local_nonpersistent_flags=()
    local flags_with_completion=()
    local flags_completion=()
    local commands=("helm")
    local must_have_one_flag=()
    local must_have_one_noun=()
    local last_command
    local nouns=()

    __helm_handle_word
}

if [[ $(type -t compopt) = "builtin" ]]; then
    complete -o default -F __start_helm helm
else
    complete -o default -o nospace -F __start_helm helm
fi

# ex: ts=4 sw=4 et filetype=sh

# Hook the command used to generate the completion script
# to the helm completion function to handle the case where
# the user renamed the helm binary
if [[ $(type -t compopt) = "builtin" ]]; then
    complete -o default -F __start_helm microk8s.helm3
else
    complete -o default -o nospace -F __start_helm helm3
fi
