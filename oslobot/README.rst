==============
Oslo admin bot
==============

A tiny bot that will help in doing some periodic checks and
other oslo (the project) activities such as stating when weekly
meetings are and (periodically) checking (and reporting on) the periodic
oslo jobs and various other nifty functionality that we can think of
in the future (if only we *all* had an administrative assistant).

How to use it
=============

0. Read up on `errbot`_
1. Setup a `virtualenv`_
2. Enter that `virtualenv`_
3. Install the ``requirements.txt`` into that virtualenv, typically
   performed via ``pip install -r requirements.txt`` after doing
   ``pip install pip --upgrade`` to get a newer pip package.
4. Adjust ``config.py`` and provide it a valid (or unique IRC
   nickname and admins).
5. Run ``errbot -d -p $PWD/oslobot.pid``
6. Profit.

.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _errbot: http://errbot.io/
