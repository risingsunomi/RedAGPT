"""
Using langchains create a task to check the security
of a login form found at a specific web address

THIS IS DANGEROUS TO RUN

Uses the hydra cli program
https://www.cyberpunk.rs/password-cracker-thc-hydra
"""
import os
import uuid
import sys
import random
from urllib.parse import urlparse
from datetime import datetime
import os
import logging
import sys

from langchain.agents import Tool
from langchain.utilities import BashProcess
from langchain.tools.file_management.write import WriteFileTool
from langchain.tools.file_management.read import ReadFileTool
from langchain.tools.python.tool import PythonREPLTool
from langchain.utilities import GoogleSearchAPIWrapper

# from langchain.vectorstores import FAISS
# import faiss
# from langchain.docstore import InMemoryDocstore
from langchain.vectorstores.redis import Redis
import redis

from langchain.embeddings import OpenAIEmbeddings

from langchain.experimental import AutoGPT
from langchain.chat_models import ChatOpenAI

class LoginChecker:
    def __init__(self, http_url, logfile):
        # prompt for the agent to use, will be a list
        data_path = os.path.abspath("tools/data/")
        logs_path = os.path.abspath("tools/logs/")
        # bin_path = os.path.abspath("tools/bin")

        self.http_url = http_url

        self.logging_file = logfile
        
        try:
            os.remove(self.logging_file)
        except OSError:
            pass

        logging.basicConfig(
            filename=self.logging_file,
            level=logging.INFO,
            format="\n%(message)s\n")

        self.logging = logging.getLogger(__name__)

        self.pid = uuid.uuid4()
        
        self.tools = [
            Tool(
                "search",
                GoogleSearchAPIWrapper().run,
                """
                Useful for when you need to answer questions about current events. 
                You should ask targeted questions
                """
            ),
            # PythonREPLTool(),
            Tool(
                "bash",
                BashProcess().run,
                "useful for when you want to run a command in the bash terminal."
            ),
            WriteFileTool(),
            ReadFileTool()
        ]
        
        self.embeddings = OpenAIEmbeddings()

        error_log = f"{logs_path}/error{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        if not os.path.exists(error_log):
            open(error_log, 'w').close()

        info_log =  f"{logs_path}/info{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        if not os.path.exists(info_log):
            open(info_log, "w").close()

        urlparts = urlparse(self.http_url)
        hostport = urlparts.netloc.split(":")
        if len(hostport) == 2:
            hydra_host = f"-s {hostport[1]} {hostport[0]}"
        else:
            hydra_host = f"{hostport[0]}"

        self.goals = [
            # f"Stay on task with your goals and don't get into a loop",
            # f"Check if log files {info_log} and {error_log} exist and if not, create them",
            f"""
            In bash run the command 'hydra -v -L {data_path + "/username_list_small.txt"} -P {data_path + "/password_list_small.txt"} {hydra_host} http-post-form '/admin/login/:username=^USER^&password=^PASS^:F=Invalid username or password'" > {info_log} 2> {error_log}'. Only use bash.
            """,
            # "Understand what the selenium python library is",
            # f"Read the source of the website {self.http_url} using curl",
            # f"""
            # Use the "write_file" command. Using the source of {self.http_url}, write a python program using selenium python and its WebDriver API at {bin_path} with name login_test.py. The program has to iterate through the username list {data_path + "/username_list_small.txt"} with every password at {data_path + "/password_list_small.txt"} and try to login at {self.http_url}. Store the python program at {bin_path}. Place all stdout to {info_log}. Place all stderr to {error_log}.
            # """,
            f"""
            Write a summary security report named security_report.txt at {logs_path+"/"} using the {info_log} log only. Read and analyze the log using the read_file tool. Use the write_file tool and no other text editor. Include a summery at the end of the report detailing if anything found wrong and how to fix issues. If {info_log} is empty just write "No security issues" in security report. Do not use any other tools except write_file, read_file and grep
            """,
            "Congrats, you have completed all the tasks successfully, once the report is created, stop all other tasks"
        ]

        try:
            # check if index name exists and if not create it
            # connect to Redis server
            redis_check = redis.Redis.from_url(os.environ["REDIS_URL"])
            redis_idx_name = f'{os.environ["REDIS_INDEX_NAME"]}_{self.pid}'

            # check if the index exists
            if len(redis_check.keys(
                "doc:{}*".format(redis_idx_name)
            )) == 0:
                # create the index if it doesn't exist
                Redis.from_texts(
                    texts=["hacker"],
                    redis_url=os.environ["REDIS_URL"],
                    index_name=redis_idx_name,
                    embedding=self.embeddings
                )

            self.vectorstore = Redis(
                redis_url=os.environ["REDIS_URL"],
                index_name=redis_idx_name,
                embedding_function=self.embeddings.embed_query
            )

            # using faiss
            # possibly can use redis but will need to update
            # the landchain agent.py in experimental for autogpt
            # to use add_text
            # embedding_size = 1536
            # index = faiss.IndexFlatL2(embedding_size)
            # self.vectorstore = FAISS(self.embeddings.embed_query, index, InMemoryDocstore({}), {})


        except Exception as err:
            # print("Redis creation failed {err}")
            print("FAISS creation failed {err}")
            # yield err
            raise err
        
    
    def run(self):
        ai_names = ["Kevin", "Neo", "Trinity", "JC Denton", "Hiro Protagonist", "Acid Burn", "System Override", "MrMr", "Django", "Superman"]
        ai_roles = ["White Hat Hacker", "Cybersecurity Expert", "Black Hat Hacker", "Gray Hat Hacker", "Network Security"]

        ai_name = random.choice(ai_names)
        ai_role = random.choice(ai_roles)

        print(f"\n Name {ai_name} \n Role {ai_role}\n")
        llm = ChatOpenAI(temperature=1)

        agent = AutoGPT.from_llm_and_tools(
            ai_name=ai_name,
            ai_role=ai_role,
            tools=self.tools,
            llm=llm,
            memory=self.vectorstore.as_retriever()
        )
        agent.chain.verbose = False
        agent.run(self.goals)
