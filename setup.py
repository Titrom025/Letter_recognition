from cx_Freeze import setup, Executable

includefiles = ['model.tar', 'vocab.tar', 'Arsenal-Regular.otf']
includes = []
excludes = []
packages = []

executables = [Executable('letterRecognition.py')]

setup(name='hello_world',
      version='0.0.1',
      description='My Hello World App!',
      options = {'build_exe': {'includes':includes,'excludes':excludes,'packages':packages,'include_files':includefiles}},
      executables=executables
)