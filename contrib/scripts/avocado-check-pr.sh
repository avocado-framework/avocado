#!/bin/bash
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2017 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>

usage() {
    cat << EOF
Usage: $0 [-i] [-v] [-h] [-u] [-t] [-r] [-b] [-d] [-D]

    -i: Interactive mode (on failure allow to override result)
    -v: Verbose mode
    -h: Help
    -u: Override user name (from cfg)
    -t: Override token (from cfg)
    -r: Override remote origin (origin)
    -b: Override the target branch (\$current-branch)
    -d: Enable debug mode
    -D: Dry run (no checking/publishing)

Verifies that all commits between the oldest new commit
compare to origin/master pass the "make check" and publishes
the results to github. Example workflow:

    git checkout master
    git merge ...
    $0
    git push origin master

In order to be able to push results one has to create
~/.config/github_checker.ini with user and token in it:

    user = my_github_user
    token = 123456789012345678901234567890
    # remote, interactive
EOF
}


cleanup() {
    [ "$tmp" ] && rm "$tmp"
    [ "$BRANCH" ] && git checkout $BRANCH &>/dev/null
}

set_status() {
    # Sets status to given commit on github
    local base_url="$1"; shift      # base github repo url
    local commit="$1"; shift        # commit-sha
    local status="$1"; shift        # status (success, failure, pending, ...)
    local result_url="$1"; shift    # url to detailed results (log)
    local description="$*"          # long(er) description
    data="\"state\": \"$status\", \"description\": \"$description\", \"context\": \"manual/$GITHUB_USER\""
    [ "$result_url" ] && data+=", \"target_url\": \"$result_url\""
    if [ "$DEBUG" ]; then
        echo curl -u $GITHUB_USER:$GITHUB_TOKEN --data "{$data}" -H "Accept: application/vnd.github.v3+json" "$base_url/statuses/$commit"
        [ "$DRY" ] || curl -u $GITHUB_USER:$GITHUB_TOKEN --data "{$data}" -H "Accept: application/vnd.github.v3+json" "$base_url/statuses/$commit"
    else
        [ "$DRY" ] || curl -u $GITHUB_USER:$GITHUB_TOKEN --data "{$data}" -H "Accept: application/vnd.github.v3+json" "$base_url/statuses/$commit" &>/dev/null
    fi
}


check() {
    # Checks the current commit
    local outfile="$1"
    local status=-1
    local description="Checked by $GITHUB_USER"
    local tmp=$(mktemp)
    make check &>> "$tmp"
    if [ $? -eq 0 ]; then
        status=0
    elif [ $INTERACTIVE ]; then
        cat $tmp
        echo -ne "\e[33mUse 'y' to ignore this failure or 'a' to abort execution: \e[0m"
        read RES
        case $RES in
            "y")
                echo -e "\e[33mForce-updating results to PASS\e[0m"
                status=1
                ;;
            "a")
                echo -e "\e[33mAborting execution\e[0m"
                cleanup
                exit -1
                ;;
        esac
    fi
    if [ $status -eq -1 ]; then
        echo >> "$outfile"
        echo >> "$outfile"
        echo "------------------------------< BEGIN >------------------------------" >> "$outfile"
        cat "$tmp" >> "$outfile"
        echo "------------------------------< END >------------------------------" >> "$outfile"
    fi
    rm $tmp
    return $status
}


publish_results() {
    # Processes results, publishes log and updates status on github
    local commit="$1"; shift
    local passed="$1"; shift
    local forced="$1"; shift
    local failed="$1"; shift
    local all_failures="$1"
    local description=""
    [ "$failed" ] && status="failure" || status="success"
    [ "$all_failures" ] && [ "$all_failures" -ne 0 ] && status="failure" && description+="#failures: $all_failures; "
    [ "$passed" ] && description+="passed: ${passed:0:-1}; "
    [ "$forced" ] && description+="forced: ${forced:0:-1}; "
    [ "$failed" ] && description+="failed: ${failed:0:-1}; "
    description=${description:0:-2}
    if [ ${#description} -gt 140 ]; then
        # Description can only be 140 chars long
        if [ ${#failed} -ne 0 ]; then
            description="FAIL: ${failed[@]}"
            [ ${#description} -gt 140 ] && description="${description:0:130}..."
        else
            description="ALL PASS"
        fi
    fi
    [ "$DRY" ] || url=$(fpaste -x 604800 $tmp | tail -n 1)
    set_status "$BASE_URL" "$commit" "$status" "${url%%/raw/}" "$description"
}


# Pre-exec check
[ "$(git diff)" ] && { usage; echo; echo "Uncommitted changes present!"; exit -1; }
which fpaste &>/dev/null || { usage; echo; echo "fpaste is necessary to run this script!"; exit -1; }

# Global defaults
GIT_REMOTE="origin"

# Read config file
if [ -e "$HOME/.config/github_checker.ini" ]; then
    exec {fd}<"$HOME/.config/github_checker.ini"
    while read -u $fd line; do
        if [[ "$line" =~ ^user\ *=\ *(.*)$ ]]; then
            GITHUB_USER=${BASH_REMATCH[1]}
        elif [[ "$line" =~ ^token\ *=\ *(.*)$ ]]; then
            GITHUB_TOKEN=${BASH_REMATCH[1]}
        elif [[ "$line" =~ ^remote\ *=\ *(.*)$ ]]; then
            GIT_REMOTE=${BASH_REMATCH[1]}
        elif [[ "$line" =~ ^interactive\ *=\ *(.*)$ ]]; then
            INTERACTIVE=${BASH_REMATCH[1]}
        fi
    done
fi

# Parse arguments
while getopts "ivu:t:r:b:dhD" opt; do
    case $opt in
        i)
            INTERACTIVE=1
            ;;
        v)
            VERBOSE=1
            ;;
        u)
            GITHUB_USER="$OPTARG"
            ;;
        t)
            GITHUB_TOKEN="$OPTARG"
            ;;
        r)
            GIT_REMOTE="$OPTARG"
            ;;
        b)
            REMOTE_BRANCH="$OPTARG"
            ;;
        d)
            DEBUG=1
            ;;
        D)
            DRY=1
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$REMOTE_BRANCH" ] || REMOTE_BRANCH="$BRANCH"

if [ "$VERBOSE" ]; then
    echo "GITHUB_USER: $GITHUB_USER"
    echo "GITHUB_TOKEN_LENGTH: ${#GITHUB_TOKEN}"
    echo "GIT_REMOTE: $GIT_REMOTE"
    echo "LOCAL_BRANCH: $BRANCH"
    echo "REMOTE_BRANCH: $REMOTE_BRANCH"
fi

[ ! "$GITHUB_USER" ] || [ ! "$GITHUB_TOKEN" ] && { usage; echo; echo "Github user or token not specified" exit -1; }

# Get commit range
GIT_URL="$(git remote get-url $GIT_REMOTE)"
BASE_URL="https://api.github.com/repos/${GIT_URL:19}"
# Commits that should be part of the PR
GIT_PR_COMMITS=$(git cherry $GIT_REMOTE/$REMOTE_BRANCH | sed -n 's/+ \(.*\)/\1/p')
# All commits between first-1 commit and HEAD
GIT_RANGE=$(git rev-list --reverse $(echo "$GIT_PR_COMMITS" | head -n 1)~1..HEAD)
[ "$?" -ne 0 ] && { echo "Error parsing git range using $GIT_REMOTE/$REMOTE_BRANCH"; exit -1; }

echo "Checking $BRANCH..$GIT_REMOTE/$REMOTE_BRANCH ($(echo "$GIT_PR_COMMITS" | wc -l | xargs)/$(echo "$GIT_RANGE" | wc -l | xargs))"
if [ "$VERBOSE" ]; then
    echo "PR commits:"
    echo "$GIT_PR_COMMITS"
    echo
fi

if [ "$DEBUG" ]; then
    echo "All commits:"
    for commit in $GIT_RANGE; do
        echo "$commit" "$(echo "$GIT_PR_COMMITS" | grep -q "$commit" && echo "*")"
    done
    echo
fi

for commit in $GIT_PR_COMMITS; do
    set_status "$BASE_URL" "$commit" "pending" "" "Starting manual check"
done

[ "$VERBOSE" ] && { echo; echo "Starting incremental check"; }
all_failures=0
passed=""
forced=""
failed=""
tmp=$(mktemp /tmp/check-XXXXXX)
for commit in $GIT_RANGE; do
    if echo "$GIT_PR_COMMITS" | grep -q "$commit"; then
        if [ "$previous_pr_commit" ]; then
            # This commit belongs to PR, publish results of previous commit
            publish_results "$previous_pr_commit" "$passed" "$forced" "$failed"
            passed=""
            forced=""
            failed=""
            rm "$tmp"
            tmp="$(mktemp /tmp/check-XXXXXX)"
        fi
        previous_pr_commit=$commit
    fi
    git checkout $commit &>/dev/null
    [ "$DEBUG" ] && echo "Checking $commit"
    [ "$DRY" ] || check "$tmp"
    case $? in
        0)
            passed+="${commit:0:6},"
            echo -n "."
            echo "PASS: $commit" >> "$tmp"
            ;;
        1)
            forced+="${commit:0:6},"
            echo -n "+"
            echo "FORCE PASS: $commit" >> "$tmp"
            ;;
        *)
            all_failures=$(expr $all_failures + 1)
            failed+="${commit:0:6},"
            [ "$VERBOSE" ] && echo -e "\nFAIL: $commit" || echo -n "F"
            echo "FAIL|ERROR: $commit" >> "$tmp"
            ;;
    esac
done
if [ "$previous_pr_commit" ]; then
    publish_results "$previous_pr_commit" "$passed" "$forced" "$failed" "$all_failures"
    echo
else
    echo "No commits found/checked!"
    exit -1
fi

cleanup
