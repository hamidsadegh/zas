     Users / API
          |
       Django
     /       \
 MySQL      Redis
   |           |
 Long-term   Fast / Temporary
   data          data

        Redis
          |
       Celery
      Workers
