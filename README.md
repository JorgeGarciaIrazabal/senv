# senv (Super Environment)

senv is a tool designed to simplify the dev-environment creation, packaging, publishing, and testing
with interchangeable build systems like poetry and/or conda (even at the same time)

## Why?
Poetry and pyproject is amazing, it seems to cover most of the cases, but we think 
there are three main reasons why senv could improve your development experience.

1. **Unify the package and environment definition**
   
   Poetry does a great job unifying the definition of your package release
   and the dev environment, but it doesn't integrate very well with conda.
   Senv also allows you to define you package and dev environment
   with pyproject.toml using the conda solver (if desired)

2. **One configuration/one cli -> multiple build systems**
   
   With senv, you can create dev environments, build and publish your package with poetry and/or conda.

   It also integrates with conda-lock to maintain the dev experience with the same cli. (senv likes lock files)

3. **New ways to consume your package**

   New tools like pipx and condax expanded how people use packages. As they both create isolated environments, 
   your clis can now be published with a pinned set of dependencies preventing unexpected problems with 
   untested dependency versions. Using `senv package publish --mode --pinned-tested` will publish your package 
   with the exact dependencies that was tested, and it is smart enough to exclude the `dev-dependencies`
   
