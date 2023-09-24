import os
import glob
import streamlit as st

from web_scraper import get_markdown_from_url, create_index_from_text

from PyPDF2 import PdfReader

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import LLMChain
from langchain.llms import OpenAI, HuggingFaceHub
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.prompts import PromptTemplate

openai_api_key = os.getenv("OPENAI_API_KEY")

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Main function
def main():

    # Set up Streamlit interface
    st.markdown("<div style='text-align:center;'> <img style='width:340px;' src='https://www.ipenclosures.com.au/wp-content/uploads/IP-EnclosuresNZ-Logo-.png.webp' /></div>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>IP Enclosures AI Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Welcome to IP Enclosures AI Assistant! Please feel free to ask any question.</p>", unsafe_allow_html=True)

    # Set up memory
    msgs = StreamlitChatMessageHistory(key="langchain_messages")
    memory = ConversationBufferMemory(chat_memory=msgs)

    # Check if there are no previous chat messages
    if len(msgs.messages) == 0:
        # Display initial message only at the very start
        st.chat_message("ai").write("How can I help you?")  # AI's initial message

    # Initialize query_input as None
    query_input = None

    # Get user input for query
    query_input = st.chat_input("Your message")  # Unique key for query input

    # Display user's query in the interface if query_input is set
    if query_input:
       # Process PDF documents
        docs_directory = os.path.join(os.getcwd(), 'docs')  # Use absolute path to 'docs' directory
        pdf_files = glob.glob(os.path.join(docs_directory, '*.pdf'))

        st.session_state.docs_processed = False  # Initialize docs_processed

        for pdf_file in pdf_files:
            with open(pdf_file, 'rb') as file:
                # Perform processing on each PDF file
                raw_text = get_pdf_text([file])

                st.session_state.pdf_text = ''.join(raw_text)

        url = "https://www.ipenclosures.com.au/electrical-enclosures/"

        # Scrap website url and retrieve markdown
        markdown = get_markdown_from_url(url)

        # Combine pdf_text and markdown
        all_info = st.session_state.pdf_text + markdown

        index = create_index_from_text(all_info)

        # Get relevant data with similarity search
        retriever = index.as_retriever()

        print(f'Query: {query_input}')

        # Input query into the retriever
        nodes = retriever.retrieve(query_input)

        texts = [node.node.text for node in nodes]

        st.session_state.docs = ' '.join(texts)

        # Check if a query is provided before generating a prompt
        if query_input:
            template = "Context: "
            template += st.session_state.docs
            template += """You are an AI chatbot for IP Enclosures having a conversation with a human. 
            Please follow the following instructions:
               
            - BEFORE ANSWERING THE QUESTION, ASK A FOLLOW UP QUESTION.
            
            - USE THE CONTEXT PROVIDED TO ANSWER THE USER QUESTION. DO NOT MAKE ANYTHING UP.
            
            - IF RELEVANT, BREAK YOUR ANSWER DO INTO STEPS
            
            - If suitable to the answer, provide any recommendations to products.
            
            - FORMAT YOUR ANSWER IN MARKDOWN
            
            - ALWAYS ASK FOLLOW UP QUESTIONS!

            - SHOW RELEVANT IMAGES OF PRODUCTS

            {history}
            Human: {human_input}
            AI: """

            prompt = PromptTemplate(input_variables=["history", "human_input"], template=template)
            llm_chain = LLMChain(llm=OpenAI(openai_api_key=openai_api_key), prompt=prompt, memory=memory)

            # Render current messages from StreamlitChatMessageHistory
            for msg in msgs.messages:
                st.chat_message(msg.type).write(msg.content)

            # If user inputs a new prompt, generate and draw a new response
            if query_input:
                
                st.chat_message("human").write(query_input)
        
                # Note: new messages are saved to history automatically by Langchain during run
                response = llm_chain.run(query_input)

                print(f'Response: {response}')

                st.chat_message("ai").write(response)

if __name__ == '__main__':
    main()
