"""
Add directives for writing exercises and solutions. This extension supports:

   .. exercise:: Name

       Any content here...

       .. solution

           Solution takes place here...

To summarize:

    - Exercises are automatically numbered "Exercise 1.1" (section number + exercise number)
    - If a `.. all-exercises::`, the exercises are mentionned where, the `exercise` directive
      is replaced with a reference to the exercise
    - Solutions can be hidden with `:hidden:`
"""
from docutils import nodes

from sphinx.util.console import colorize
from sphinx.locale import _
from sphinx import addnodes
from docutils.parsers.rst import Directive
from sphinx.util.docutils import SphinxDirective
from sphinx.environment.adapters.toctree import TocTree
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.util import url_re

import logging

logger = logging.getLogger(__name__)


class exercise(nodes.Admonition, nodes.Element):
    pass


class all_exercises(nodes.General, nodes.Element):
    pass


class solution(nodes.Admonition, nodes.Element):
    pass


class AllExercisesDirective(SphinxDirective):
    """ Directive replaced with all exercises found in all documents:
        Section number, subsection, exercises...
    """
    def run(self):
        return [all_exercises()] # Let it process later once the toctree is built


class ExerciseDirective(SphinxDirective):
    final_argument_whitespace = True
    has_content = True
    optional_arguments = 1

    def run(self):
        self.assert_has_content()

        id = 'exercise-%d' % self.env.new_serialno('sphinx.ext.exercises#exercises')

        target_node = nodes.target('', '', ids=[id])

        node = exercise('\n'.join(self.content), **self.options)
        node += nodes.title(_('Title'), _('Title'))
        self.state.nested_parse(self.content, self.content_offset, node)

        if not hasattr(self.env, 'exercises_all_exercises'):
            self.env.exercises_all_exercises = []

        self.env.exercises_all_exercises.append({
            'docname': self.env.docname,
            'lineno': self.lineno,
            'node': node,
            'target': target_node,
        })

        #logger.warning(colorize('yellow', 'ExerciseDirective %s' % id))

        return [target_node, node]


class SolutionDirective(nodes.Admonition):
    pass

def visit_exercise(self, node, name=''):
    #logger.warning(colorize('blue', 'visit_exercises'))
    #print('visit ', repr(node), id(node))
    self.body.append(self.starttag(node, 'div', CLASS=('exercise ' + name)))
    if hasattr(node, 'exnum'): self.body.append('secnum: %s' % str(node.exnum))

def depart_exercise(self, node=None):
    self.body.append('</div>\n')


def visit_solution(self, node, name=''):
    self.body.append(self.starttag(node, 'div', CLASS=('solution')))


def depart_solution(self, node=None):
    self.depart_admonition(node)

def no_visit(self, node=None):
    pass

def process_exercise_nodes(app, doctree, fromdocname):
    env = app.builder.env

    for node in doctree.traverse(exercise):
        docname = 'foo'
        para = nodes.paragraph()
        filename = env.doc2path(docname, base=None)

        number = '0'
        print('Z.', id(node))
        if hasattr(node, 'exnum'):
            print('HASIT')

        print('node-id', node['ids'])
        #number = '.'.join(map(str, node.exnum))
        description = app.config.numfig_format['exercise'] % number


        ref = nodes.reference('','')
        innernode = nodes.Text(description, description)
        ref['refdocname'] = 'docname'
        ref['refuri'] = app.builder.get_relative_uri(fromdocname, 'foo')
        ref['refuri'] += '#foobar'
        ref.append(innernode)
        para += ref

        node.parent.replace(node, para)

    for node in doctree.traverse(all_exercises):
        content = []
        for ex in app.env.all_exercises:
            content.append(ex)

        node.replace_self(content)


class ExercisesCollector(EnvironmentCollector):
    def clear_doc(self, app, env, docname):
        pass

    def process_doc(self, app, doctree):
        pass

    def get_updated_docs(self, app, env):
        def traverse_all(env, docname):
            doctree = env.get_doctree(docname)

            for toc in doctree.traverse(addnodes.toctree):
                for _, subdocname in toc['entries']:
                    traverse_all(env, subdocname)

            for node in doctree.traverse(exercise):
                self.process_exercise(env, node, docname)

        traverse_all(env, env.config.master_doc)

        return []

    def process_exercise(self, env, node, docname):
        node.exnum = env.toc_fignumbers.get(docname, {}).get('exercise', {}).get(node['ids'][0])
        print('A.', id(node))

        if not hasattr(env, 'all_exercises'):
            env.all_exercises = []

        env.all_exercises.append(node)

def init_numfig_format(app, config):
    config.numfig_format.update({'exercise': _('Exercise %s')})

def setup(app):
    no_visits = (no_visit, no_visit)
    visitors = (visit_exercise, depart_exercise)

    app.add_config_value('hide_solutions', False, 'html')

    app.add_enumerable_node(exercise, 'exercise',
        html=visitors,
        latex=no_visits,
        text=visitors,
        man=no_visits
    )

    app.add_node(solution,
        html=(visit_solution, depart_solution),
        latex=no_visits,
        man=no_visits
    )


    app.add_directive('exercise', ExerciseDirective)
    app.add_directive('solution', SolutionDirective)
    app.add_directive('all-exercises', AllExercisesDirective)

    app.connect('config-inited', init_numfig_format)
    app.connect('doctree-resolved', process_exercise_nodes)

    app.add_env_collector(ExercisesCollector)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }