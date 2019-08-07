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

from sphinx.locale import _
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives.admonitions import Hint
from sphinx.util.docutils import SphinxDirective
from sphinx.environment.adapters.toctree import TocTree
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.util import url_re
from sphinx.domains import Domain

import uuid

class exercise(nodes.Admonition, nodes.Element):
    pass

class all_exercises(nodes.Element):
    pass 

class solution(nodes.Admonition, nodes.Element):
    pass

class SolutionDirective(Hint):
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

        text = '\n'.join(self.content)

        admonition_node = exercise(text, **self.options)
        admonition_node.signature = str(uuid.uuid5(uuid.NAMESPACE_OID, text))

        self.add_name(admonition_node)

        admonition_node.title = self.arguments[0] if len(self.arguments) > 0 else ''

        self.state.nested_parse(self.content, self.content_offset,
                                admonition_node)

        if not hasattr(self.env, 'exercises'):
            self.env.exercises = []
        self.env.exercises.append({
            'docname': self.env.docname,
            'lineno': self.lineno,
            'node': admonition_node.deepcopy()
        }) 
        
        # # Create a reference
        # newnode = nodes.reference('', '')
        # innernode = nodes.emphasis(_('here'), _('here'))
        # newnode['refdocname'] = self.env.docname
        # newnode['refuri'] = 'relative-url' #app.builder.get_relative_uri(self.env.docname, 'blabla')
        # newnode['refuri'] += '#' + 'blibli'
        # newnode.append(innernode)   

        return [admonition_node]


def visit_exercise(self, node, name=''):
    number = '.'.join(map(str, self.builder.env.toc_exercises[node.signature]))
    
    node.title = 'lala'
    print(self.builder.env.toc_exercises)
    self.body.append(self.starttag(node, 'div', CLASS=('exercise ' + name)))
    self.body.append('<h3>Exercise %s: %s</h3>' % (number, node.title))


def depart_exercise(self, node=None):
    self.body.append('</div>\n')


def visit_solution(self, node, name=''):
    self.body.append(self.starttag(node, 'div', CLASS=('solution')))


def depart_solution(self, node=None):
    self.depart_admonition(node)

def no_visit(self, node=None):
    pass

class ExercisesCollector(EnvironmentCollector):

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname):
        if not hasattr(env, 'toc_exercise_numbers'):
            env.toc_exercise_numbers =  {}

        env.toc_exercise_numbers.pop(docname, None)

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        pass

    def get_updated_docs(self, app: Sphinx, env: BuildEnvironment):
        return self.assign_exercise_numbers(env)

    def assign_exercise_numbers(self, env: BuildEnvironment):
        """Assign a exercise number to each exercise under a numbered toctree."""

        rewrite_needed = []

        assigned = set()  # type: Set[str]
        old_exercise_numbers = env.toc_exercise_numbers
        env.toc_exercise_numbers = {}
        env.toc_exercises = {}
        exercise_counter = {}  # type: Dict[str, Dict[Tuple[int, ...], int]]

        def get_section_number(docname, section):
            anchorname = '#' + section['ids'][0]
            section_numbers = env.toc_secnumbers.get(docname, {})
            if anchorname in section_numbers:
                section_number = section_numbers.get(anchorname)
            else:
                section_number = section_numbers.get('')

            return section_number or tuple()

        def get_next_exercise_number(section_number):
            section = section_number[0]
            exercise_counter[section] = exercise_counter.get(section, 0) + 1
            return (section, exercise_counter[section],)

        def register_exercise_number(docname, section_number, exercise):
            env.toc_exercise_numbers.setdefault(docname, {})
            number = get_next_exercise_number(section_number)
            env.toc_exercise_numbers[docname][exercise.signature] = number
            env.toc_exercises[exercise.signature] = number

        def _walk_doctree(docname, doctree, section_number) -> None:
            for subnode in doctree.children:
                if isinstance(subnode, nodes.section):
                    next_section_number = get_section_number(docname, subnode)
                    if next_section_number:
                        _walk_doctree(docname, subnode, next_section_number)
                    else:
                        _walk_doctree(docname, subnode, section_number)
                elif isinstance(subnode, addnodes.toctree):
                    for title, subdocname in subnode['entries']:
                        if url_re.match(subdocname) or subdocname == 'self':
                            # don't mess with those
                            continue

                        _walk_doc(subdocname, section_number)
                elif isinstance(subnode, exercise):
                    register_exercise_number(docname, section_number, subnode)
                    _walk_doctree(docname, subnode, section_number)

                elif isinstance(subnode, nodes.Element):
                    _walk_doctree(docname, subnode, section_number)

        def _walk_doc(docname, section_number) -> None:
            if docname not in assigned:
                assigned.add(docname)
                doctree = env.get_doctree(docname)

                print("MAMAN", doctree.traverse(exercise))
                _walk_doctree(docname, doctree, section_number)

        _walk_doc(env.config.master_doc, tuple())
        for docname, exercise_number in env.toc_exercise_numbers.items():
            if exercise_number != old_exercise_numbers.get(docname):
                rewrite_needed.append(docname)

        return rewrite_needed

class ExerciseDomain(Domain):

    name = 'exercise'
    label = 'Exercise Sample'
    # roles = {
        
    # }
    # directives = {
    #     'exercise': ExerciseDirective,
    # }
    # indices = {
    #     ExerciseIndex
    # }
    # initial_data = {
    #     'exercises': []
    # }

def process_exercise_nodes(app, doctree, fromdocname):
    env = app.builder.env
    print("after %s  ", fromdocname)
    

    for node in doctree.traverse(exercise):
        node.replace_self([])

    for node in doctree.traverse(all_exercises):
        # if not app.config.todo_include_todos:
        #     node.replace_self([])
        #     continue

        content = []

        for info_exercise in env.exercises:
            para = nodes.paragraph()
            filename = env.doc2path(info_exercise['docname'], base=None)
            description = (
                _('(The original entry is located in %s, line %d and can be found ') %
                (filename, info_exercise['lineno']))
            para += nodes.Text(description, description)

            # Create a reference
            # newnode = nodes.reference('', '')
            # innernode = nodes.emphasis(_('here'), _('here'))
            # newnode['refdocname'] = todo_info['docname']
            # newnode['refuri'] = app.builder.get_relative_uri(
            #     fromdocname, todo_info['docname'])
            # newnode['refuri'] += '#' + todo_info['target']['refid']
            # newnode.append(innernode)
            # para += newnode
            # para += nodes.Text('.)', '.)')

            # Insert into the todolist
            content.append(info_exercise['node'])

        node.replace_self(content)    



def setup(app):
    no_visits = (no_visit, no_visit)
    visitors = (visit_exercise, depart_exercise)

    app.add_config_value('hide_solutions', False, 'html')

    app.add_node(exercise, html=visitors, latex=no_visits, text=visitors, man=no_visits)
    app.add_node(solution, 
        html=(visit_solution, depart_solution), 
        latex=no_visits, 
        man=no_visits
    )

    app.add_directive('exercise', ExerciseDirective)
    app.add_directive('solution', SolutionDirective)
    app.add_directive('all-exercises', AllExercisesDirective)

    app.connect('doctree-resolved', process_exercise_nodes)

    app.add_env_collector(ExercisesCollector)
    app.add_domain(ExerciseDomain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }