# Visitor Badge

Count visitors for your GitHub, Blog or Portfolio Site in just one line markdown code or one api call

![visitor badge](https://visitor-badge.one9x.com/badge?page_id=visitor-badge)


## How to use?

If you know how to add picture in markdown or image in html, then you are good to go.

#### Markdown

```md
![visitors](https://visitor-badge.example.net/badge?page_id={page.id}&left_color=red&right_color=green)
```

#### HTML

```html
<img src="https://visitor-badge.example.net/badge?page_id={page.id}&left_color=red&right_color=green" />
```

#### API

```bash
curl -X GET "http://visitor-badge.example.net/count?page_id={page.id}"  

// output: {"value": 100}
```

### Options
| Params          | Required | Default | Description                                                  |
| --------------- | -------- | ------- | ------------------------------------------------------------ |
| `padge_id`      | Required | null    | Unique string to best represent your page                    |
| `namespace`     | Optional | default | Unique key to group all your pages and avoid conflict with others |
| `read`          | Optional | false   | Only return existing count, don't increment                   |
| `unique (experimental)` | Optional | false | Only count unique request within a given window as set by timeframe param. Note: this is experimental flag may not work as desired |
| `timeframe`     | Optional | 600     | Time window for which a request is considered as duplicate if unique param is set |
| *`left_color` | Optional | #595959 | Left side color of the badge                                  |
| *`left_text`  | Optional | visitor | Left side text of the badge                                   |
| *`right_color`| Optional | #1283c3 | Right side color of the badge                                 |

**Note:** * options only applied for path `/badge`

## Public Servers
- URL: https://visitor-badge.one9x.com

    Free: Yes

    Please be aware that this server is hosted on a homelab environment, which may result in occasional downtime or data loss. To minimize the risk of data loss, nightly data snapshots are taken at 12:00 AM IST.

## What's next?

What new features will be available in the next release?

- Data backup

    Regularly backup the latest data into a safe place weekly and make it recoverable

- Stable unique count implementation
    
    Implement a stable solution to track unique visitor

- Namespace Management

  Ability to set configuration at namespace level

Have something in mind? [Just tell me...](https://github.com/ramank775/visitor-badge/issues/new)

#### Fork From
> jwenjian：[https://github.com/jwenjian/visitor-badge](https://github.com/jwenjian/visitor-badge)