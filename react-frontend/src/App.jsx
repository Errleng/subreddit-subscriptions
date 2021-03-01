import './App.css';
import {useEffect, useState} from 'react';
import Subreddit from "./Subreddit";

function App() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [subredditNames, setSubredditNames] = useState([]);

    useEffect(() => {
        fetch('/subreddit/favorites')
            .then((res) => res.json())
            .then((json) => {
                setIsLoaded(true);
                setSubredditNames(json);
            });
    }, []);

    if (isLoaded) {
        const subredditElements = subredditNames.map((name) => {
            return <Subreddit key={name} name={name}/>
        });

        return (
            <div className="App">
                <header className="App-header">
                    {subredditElements}
                </header>
            </div>
        );
    } else {
        return (
            <div className="App">
                <header className="App-header">
                    <h1>Loading subreddits...</h1>
                </header>
            </div>
        );
    }
}

export default App;
