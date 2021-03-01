import React from 'react';
import ImageComponent from "./ImageComponent";

function Submission(props) {
    const {id, shortlink, title, score, upvoteRatio, age, image_previews} = props.data;
    const info = [score, upvoteRatio, age].filter(Boolean).join(', ');

    const imageElements = (image_previews === undefined)
        ? null
        : image_previews.map((preview) => {
            return <ImageComponent key={preview} image_link={preview}/>
        });

    return (
        <div id={`post-${id}`}>
            <a className="App-link" href={shortlink} rel="noopener noreferrer" target="_blank">
                <p>{title} ({info})</p>
                {imageElements}
            </a>
        </div>
    );
}

export default Submission;
