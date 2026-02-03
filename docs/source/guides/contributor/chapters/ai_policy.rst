Policy for AI-Generated Code
============================

Introduction and Purpose
------------------------

This policy outlines the guidelines and requirements for the use of
Artificial Intelligence (AI) generated code within the Avocado
framework project. As AI code generation tools become increasingly
prevalent, it is crucial to establish clear standards to ensure
transparency, maintain code quality, uphold licensing integrity, and
address potential ethical and security concerns. This policy aims to
facilitate responsible and effective integration of AI tools while
safeguarding the principles of open-source collaboration.

What is AI-Generated Code
-------------------------

Any code, code snippets, configurations, documentation, or other
programmatic assets produced, suggested, or significantly modified by an
artificial intelligence model, tool, or service. This includes code that
is directly used, or heavily adapted from AI suggestions.

Transparency and Disclosure
---------------------------

All contributors are required to be transparent about the use of
AI-generated code.

-   **Explicit Attribution:** When submitting a Pull Request (PR) or
    commit that includes AI-generated code, contributors **must**
    explicitly state that AI tools were used. This has to be done in the
    commit message and PR description.

    -   **Example Commit Message/PR Description:**

        .. code-block:: python
           :emphasize-lines: 5,6,7

            header          <- Limited to 72 characters. No period.
                            <- Blank line
            message         <- Any number of lines, limited to 72 characters per line.
                            <- Blank line
            Assisted-by:    <- artificial intelligence model, tool, or service which
                            has been used and how big part of contribution has
                            been generated (percentage)
            Reference:      <- External references, one per line (issue, trello, ...)
            Signed-off-by:  <- Signature and acknowledgment of licensing terms when
                            contributing to the project (created by git commit -s)

-   **Originality:** If AI was used as a brainstorming or refactoring
    tool, but the final code is substantially original and reviewed by
    the contributor, a general disclosure in the PR description is
    sufficient.

Licensing and Copyright
-----------------------

Contributors are responsible for ensuring that AI-generated code complies
with the Avocado's license (GPLv2).

-   **Be Alert to Possible Copyright Issues:** Do not assume that
    AI-generated code is free of licensing obligations or copyright.
    Treat it with the same diligence as code copied from other sources.
    To the extent practical, ensure that AI-generated code does not
    infringe third-party copyrights.
-   **Review for Training Data Leakage:** Contributors are expected to
    enable any code similarity matching or blocking functionality offered
    by their AI tools if it is available. This helps to identify or
    prevent potential leakage from proprietary or incompatibly licensed
    training data. If such instances are identified by the contributor,
    the contributor must either (a) ensure that the AI-generated code is
    used in a manner that complies with its license, and ensure that such
    license is compatible with the license of the project, or (b) the
    code should be re-written before submission.

Code Quality, Review, and Testing
----------------------------------

AI-generated code must adhere to the same quality standards as
human-written code.

-   **Human Review Required:** All AI-generated code, regardless of its
    source, **must** be thoroughly reviewed by a human contributor. This
    review should be as rigorous, if not more so, than the review of
    human-written code.

AI contribution best practise
-----------------------------

-   **AI as an Assistant:** AI tools are encouraged as assistants for
    boilerplate generation, refactoring suggestions, debugging, or
    exploring different approaches. They should not replace critical
    thinking, understanding, and human review.
-   **Understanding is Key:** Contributors must fully understand any
    AI-generated code they submit. Do not submit code you do not
    comprehend or cannot debug yourself.
-   **Iterative Refinement:** Do not blindly accept AI output.

Enforcement and Dispute Resolution
----------------------------------

-   **Non-Compliance:** Failure to adhere to this policy may result in the
    rejection of Pull Requests.
-   **Disputes:** Any disputes or concerns regarding the use of
    AI-generated code will be discussed and resolved by the Avocado
    maintainers.

Disclaimer
----------

This policy is a living document and will be updated as AI technology
evolves and best practices emerge. Contributors are encouraged to provide
feedback and suggestions to improve this policy over time.
