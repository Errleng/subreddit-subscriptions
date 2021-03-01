import React from 'react';

function ImageComponent(props) {
    const {image_link} = props;

    if (image_link !== null) {
        return (
            <img alt="Submission preview" src={image_link}/>
        );
    } else {
        return null;
    }
}

export default ImageComponent;
