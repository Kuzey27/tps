#!/usr/bin/python2.7

import json
import os
import six
import subprocess


valid_problem_types = ('batch', 'interactive', 'communication', 'output-only', 'two-phase')
valid_verdicts = ('model_solution', 'correct', 'time_limit', 'memory_limit', 'incorrect', 'runtime_error', 'failed', 'time_limit_and_runtime_error')

HEADER = '\033[95m'
OKBLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

errors = []
warnings = []
namespace = ''


def error(description):
    errors.append(FAIL + 'ERROR: {} - {}'.format(namespace, description) + ENDC)


def warning(description):
    warnings.append(YELLOW + 'WARNING: {} - {}'.format(namespace, description) + ENDC)


def check_keys(data, required_keys, json_name):
    for key in required_keys:
        if key not in data:
            error('{} is required in {}'.format(key, json_name))


def error_on_duplicate_keys(ordered_pairs):
    data = {}
    for key, value in ordered_pairs:
        if key in data:
            error("duplicate key: {}".format(key))
        else:
            data[key] = value
    return data


def load_data(json_file, required_keys=()):
    with open(json_file, 'r') as f:
        data = json.load(f, object_pairs_hook=error_on_duplicate_keys)
    check_keys(data, required_keys, json_file)
    return data


def get_list_of_files(directory):
    return list(set(os.listdir(directory)) - {'testlib.h'})


def verify_problem():
    problem = load_data('problem.json', ['name', 'title', 'type', 'time_limit', 'memory_limit'])

    git_origin_name = subprocess.check_output('git remote get-url origin | rev | cut -d/ -f1 | rev | cut -d. -f1', shell=True).strip()

    if not isinstance(problem['name'], six.string_types):
        error('name is not a string')
    elif problem['name'] != git_origin_name:
        warning('problem name and git project name are not the same')

    if not isinstance(problem['title'], six.string_types):
        error('title is not a string')

    if not isinstance(problem['type'], six.string_types) or problem['type'] not in valid_problem_types:
        error('type should be one of {}'.format('/'.join(valid_problem_types)))

    if not isinstance(problem['time_limit'], float) or problem['time_limit'] < 0.5:
        error('time_limit should be a number greater or equal to 0.5')

    memory = problem['memory_limit']
    if not isinstance(memory, int) or memory < 1 or memory & (memory - 1) != 0:
        error('memory_limit should be an integer that is a power of two')

    return problem


def verify_subtasks():
    subtasks = load_data('subtasks.json', ['samples'])

    indexes = set()
    score_sum = 0

    validators = get_list_of_files('validator/')
    used_validators = set()

    for name, data in subtasks.iteritems():
        if not isinstance(data, dict):
            error('invalid data in {}'.format(name))
            continue

        check_keys(data, ['index', 'score', 'validators'], name)

        indexes.add(data['index'])

        if not isinstance(data['score'], int) or data['score'] < 0:
            error('score should be a non-negative integer in subtask {}'.format(name))
        elif name == 'samples':
            if data['score'] != 0:
                error('samples subtask score is non-zero')
        else:
            score_sum += data['score']

        if not isinstance(data['validators'], list):
            error('validators is not an array in subtask {}'.format(name))
        else:
            for index, validator in enumerate(data['validators']):
                if not isinstance(validator, six.string_types):
                    error('validator #{} is not a string in subtask {}'.format(index, name))
                elif validator not in validators:
                    error('{} does not exists'.format(validator))
                else:
                    used_validators.add(validator)

    for unused_validator in set(validators) - used_validators:
        warning('unused validator {}'.format(unused_validator))

    if score_sum != 100:
        error('sum of scores is {}'.format(score_sum))
    for i in range(len(subtasks)):
        if i not in indexes:
            error('missing index {} in subtask indexes'.format(i))

    return subtasks


def verify_verdict(verdict, key_name):
    if not isinstance(verdict, six.string_types) or verdict not in valid_verdicts:
        error('{} verdict should be one of {}'.format(key_name, '/'.join(valid_verdicts)))


def verify_solutions(subtasks):
    solutions = load_data('solutions.json')

    solution_files = set(get_list_of_files('solution/'))

    for solution in solutions:
        if solution not in solution_files:
            error('{} does not exists'.format(solution))
            continue
        solution_files.remove(solution)

        data = solutions[solution]

        check_keys(data, ['verdict'], solution)
        verify_verdict(data['verdict'], solution)

        if 'except' in data:
            exceptions = data['except']
            if not isinstance(exceptions, dict):
                error('invalid except format in {}'.format(solution))
            else:
                for subtask_verdict in exceptions:
                    if subtask_verdict not in subtasks:
                        error('subtask "{}" is not defined and cannot be used in except'.format(subtask_verdict))
                    else:
                        verify_verdict(exceptions[subtask_verdict], '{}.except.{}'.format(solution, subtask_verdict))

    for solution in solution_files:
        error('{} is not represented'.format(solution))


if __name__ == '__main__':
    namespace = 'problem.json'
    verify_problem()

    namespace = 'subtasks.json'
    subtasks = verify_subtasks()

    namespace = 'solutions.json'
    verify_solutions(subtasks)

    for error in errors:
        print error

    if not errors:
        if warnings:
            print YELLOW + 'verified ' + ENDC + 'but there are some warnings'
        else:
            print GREEN + 'verified.' + ENDC

    for warning in warnings:
        print warning