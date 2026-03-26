Traceback (most recent call last):
  File "/Users/aditewari/Desktop/RAGAppBackend/main.py", line 119, in <lambda>
    result = await ctx.step.run("clear-all-context", lambda:_clear_all_context(), output_type=RAGClearResult)
                                                            ~~~~~~~~~~~~~~~~~~^^
  File "/Users/aditewari/Desktop/RAGAppBackend/main.py", line 117, in _clear_all_context
    return RAGClearResult(message)
TypeError: BaseModel.__init__() takes 1 positional argument but 2 were given
