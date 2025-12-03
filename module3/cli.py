import time


def run_interactive_cli(rag_service):
    """
    Runs the interactive CLI loop for the RAG service.

    Args:
        rag_service: An initialized instance of SECRAGService.
    """
    # ---------------------------------------------------------
    # CONFIGURATION & STATE
    # ---------------------------------------------------------
    # SET DEFAULT TICKER HERE
    current_ticker = "AAPL"

    examples = [
        "Please provide a brief analysis of the data relating to Apple's stockholders equity?",
        "Is Apple paying money back to its shareholders?",
        "Are sales and profits growing?",
        "How much does Apple own (Assets) versus how much does it owe (Liabilities)?",
        "What were Apple's total sales (Revenue)?",
        "How much cash does Apple have on hand?"
    ]

    # ---------------------------------------------------------
    # HELPER FUNCTIONS
    # ---------------------------------------------------------
    def print_help():
        print("\n" + "=" * 60)
        print("COMMANDS:")
        print("  /ticker <SYMBOL> : Switch company (e.g., '/ticker AAPL')")
        print("  /all             : Clear filter (search all filings)")
        print("  /examples        : Show example questions")
        print("  /quit            : End the session")
        print("-" * 60)
        print(f"EXAMPLE QUESTIONS (Type 1-{len(examples)} to select):")
        for i, ex in enumerate(examples, 1):
            print(f"  {i}. {ex}")
        print("=" * 60)

    # ---------------------------------------------------------
    # MAIN CLI LOOP
    # ---------------------------------------------------------
    print("\n[SYSTEM READY]")
    print(f"Default filter active: {current_ticker}")
    print_help()

    while True:
        try:
            # Dynamic prompt showing current context
            context_label = f"[{current_ticker}]" if current_ticker else "[ALL FILES]"
            user_input = input(f"\nUser {context_label} >> ").strip()

            # Handle empty input
            if not user_input:
                continue

            # Handle Exit
            if user_input.lower() in ['/quit', '/exit', 'exit', 'quit']:
                print("Closing connection...")
                break

            # Handle Help
            if user_input.lower() in ['/help', '/examples', 'help']:
                print_help()
                continue

            # Handle Ticker Change
            if user_input.lower().startswith('/ticker'):
                parts = user_input.split()
                if len(parts) > 1:
                    current_ticker = parts[1].upper()
                    print(f"System: Filter switched to {current_ticker}")
                else:
                    print("System: Please provide a ticker symbol (e.g., /ticker MSFT)")
                continue

            # Handle Clear Filter
            if user_input.lower() == '/all':
                current_ticker = None
                print("System: Filter cleared. Searching across all available filings.")
                continue

            # Handle Numeric Shortcuts
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(examples):
                    user_input = examples[idx]
                    print(f"System: Selected Example -> '{user_input}'")
                else:
                    print(f"System: Invalid selection. Please enter a number between 1 and {len(examples)}.")
                    continue

            # Process Question
            print(f"Thinking...", end="", flush=True)
            start_time = time.time()

            # Get Answer
            answer = rag_service.ask(
                user_input,
                ticker=current_ticker
            )

            elapsed_time = time.time() - start_time
            print(f"\r", end="")  # Clear the "Thinking..." line

            # Display Output
            print("-" * 60)
            print(f"AI Response ({elapsed_time:.2f}s):")
            print(answer)
            print("-" * 60)

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")