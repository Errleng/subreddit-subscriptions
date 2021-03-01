import React, {useEffect, useState} from 'react';
import Submission from "./Submission";

function Subreddit(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [submissionList, setSubmissionList] = useState([]);
    const {name} = props;

    useEffect(() => {
        fetch(`/subreddit/${name}`)
            .then((res) => res.json())
            .then((json) => {
                setSubmissionList(json);
                setIsLoaded(true);
            });
    }, []);

    if (isLoaded) {
        const submissionElements = submissionList.map((submission) => {
            return <Submission key={submission.id} data={submission}/>
        });
        return (
            <div>
                <h1>r/{name}</h1>
                <div>
                    {submissionElements}
                </div>
            </div>
        );
    } else {
        return <h4>Loading r/{name}...</h4>
    }
}

export default Subreddit;
