
The app has been tested in a linux server with GPU access.

1. Create a virtual environment

```
conda create -n trail python=3.9
```

2. Install streamlit .whl in the directory

```
pip install streamlit-1.39.0-py2.py3-none-any.whl
```

3. Run requirement.txt to install packages

```
pip install -r requirement.txt
```

4. Unzip H&M dataset in the directory

```bash
kaggle competitions download -c h-and-m-personalized-fashion-recommendations
mkdir fashion_datset
mv h-and-m-personalized-fashion-recommendations.zip fashion_datset
jar -xvf h-and-m-personalized-fashion-recommendations.zip 
```

5. unzip the vector index

```
unzip vector_index_small.zip
```

6. Replace openai_key in the attributes.py

7. Start the streamlit server

```
streamlit run Chatbot.py --server.port 8010
ssh -NL localhost:1300:localhost:8010 USERNAME@REMOTE_SERVER_ADDRESS
```


