# `paver` based test

This test infra was built using `paver` as a mean to set the test dependency.

## Commands

#### Run all tests
```
paver
```

## Reference

#### Unused code
```
# ------------------------------------------------
# Load all tasks from task*.py files
def load_task_files():
    '''
    Load all the tasks.  Not sure if this is needed.
    ToDo: Remove this if not needed by paver
    '''
    def gen_test_file_name(filename):
        '''Trip extenstion from the filename'''
        if filename == "tasks.py" or (filename.startswith("task_") and filename.endswith(".py")):
            return filename[:-3]

    def strip_leading(package_name, *chars):
        '''Remove the staring chars from the package name'''
        for char in chars:
            while package_name.startswith(char):
                package_name = package_name[1:]
        return package_name

    script_path = os.path.dirname(__file__) or "."

    # Search for all files on and below directory of this file
    for root, _, files in os.walk(script_path):
        package_path = strip_leading(root, '.', os.sep).replace(os.sep, '.')
        for fname in files:
            module_name = gen_test_file_name(fname)
            if module_name:
                package_name = "%s.%s" % (package_path, module_name)
                try:
                    import_module(package_name)
                    print("Imported %s" % package_name)
                except StandardError as err:
                    print("Error importing %s: %s" % (os.path.join(root, fname), err))
```
