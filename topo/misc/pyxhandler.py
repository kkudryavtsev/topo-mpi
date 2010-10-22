"""
Interface class Cython pyx files.

$Id$
"""

# CEBENHANCEMENT: If we begin using Cython components, consider adding
# more features of inlinec.py (ie: test of Cython compilation, control
# over warnings).

import __main__
import_pyx = __main__.__dict__.get('import_pyx',False)

pyximported = False

if import_pyx:
    try:
        import pyximport
        pyximport.install()
        pyximported = True
    except:
        pass


def provide_unoptimized_equivalent_cy(optimized_name, unoptimized_name, local_dict):
    """
    Replace the optimized Cython component with its unoptimized
    equivalent if pyximport is not available.

    If import_pyx is True, warns about the unavailable component.
    """
    if not pyximported:
        local_dict[optimized_name] = local_dict[unoptimized_name]
        if import_pyx:
            print '%s: Cython components not available; using %s instead of %s.' \
                  % (local_dict['__name__'], unoptimized_name, optimized_name)
