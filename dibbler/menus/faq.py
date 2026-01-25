# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from .helpermenus import Menu, MessageMenu


class FAQMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Frequently Asked Questions", sql_session)
        self.items = [
            MessageMenu(
                "What is the meaning with this program?",
                """
            We want to avoid keeping lots of cash in PVVVV's money box and to
            make it easy to pay for stuff without using money.  (Without using
            money each time, that is.  You do of course have to pay for the things
            you buy eventually).

            Dibbler stores a "credit" amount for each user.  When you register a
            purchase in Dibbler, this amount is decreased.  To increase your
            credit, purchase products for dibbler, and register them using "Add
            stock and adjust credit".
            Alternatively, add money to the money box and use "Adjust credit" to
            tell Dibbler about it.
            """,
                sql_session,
            ),
            MessageMenu(
                "Can I still pay for stuff using cash?",
                """
            Please put money in the money box and use "Adjust Credit" so that
            dibbler can keep track of credit and purchases.""",
                sql_session,
            ),
            MessageMenu(
                "How do I exit from a submenu/dialog/thing?",
                'Type "exit", "q", or ^d.',
                sql_session,
            ),
            MessageMenu(
                'What does "." mean?',
                """
            The "." character, known as "full stop" or "period", is most often
            used to indicate the end of a sentence.

            It is also used by Dibbler to indicate that the program wants you to
            read some text before continuing.  Whenever some output ends with a
            line containing only a period, you should read the lines above and
            then press enter to continue.
                                  """,
                sql_session,
            ),
            MessageMenu(
                "Why is the user interface so terribly unintuitive?",
                """
            Answer #1:  It is not.

            Answer #2:  We are trying to compete with PVV's microwave oven in
            userfriendliness.

            Answer #3:  YOU are unintuitive.
            """,
                sql_session,
            ),
            MessageMenu(
                "Why is there no help command?",
                'There is.  Have you tried typing "help"?',
                sql_session,
            ),
            MessageMenu(
                'Where are the easter eggs?  I tried saying "moo", but nothing happened.',
                'Don\'t say "moo".',
                sql_session,
            ),
            MessageMenu(
                "Why does the program speak English when all the users are Norwegians?",
                "Godt spørsmål.  Det virket sikkert som en god idé der og da.",
                sql_session,
            ),
            MessageMenu(
                "Why does the screen have strange colours?",
                """
            Type "c" on the main menu to change the colours of the display, or
            "cs" if you are a boring person.
            """,
                sql_session,
            ),
            MessageMenu(
                "I found a bug; is there a reward?",
                """
            No.

            But if you are certain that it is a bug, not a feature, then you
            should fix it (or better: force someone else to do it).

            Follow this procedure:

            1. Check out the Dibbler code: https://github.com/Programvareverkstedet/dibbler

            2. Fix the bug.

            3. Check that the program still runs (and, preferably, that the bug is
               in fact fixed).

            4. Commit.

            5. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ git pull

            6. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            """,
                sql_session,
            ),
            MessageMenu(
                "My question isn't listed here; what do I do?",
                """
            DON'T PANIC.

            Follow this procedure:

            1. Ask someone (or read the source code) and get an answer.

            2. Check out the Dibbler code: https://github.com/Programvareverkstedet/dibbler

            3. Add your question (with answer) to the FAQ and commit.

            4. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ git pull

            5. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            """,
                sql_session,
            ),
        ]
